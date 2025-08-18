
from anynet import tls, http
from nintendo import resources
from nintendo.switch import common, dauth
import base64

import logging
logger = logging.getLogger(__name__)


USER_AGENT = "NintendoSDK Firmware/%s (platform:NX; did:%016x; eid:lp1)"

API_VERSION = {
	2000: 1,
	2001: 1,
	2010: 1,
	2011: 1,
	2015: 1,
	2020: 1,
	2030: 1,
}

LATEST_VERSION = 2030

	
class VermillionError(Exception):
	API_NOT_FOUND = 5011
	INVALID_AUTH_TOKEN = 5014
	
	def __init__(self, response):
		self.response = response
		self.code = int(response.json["errors"][0]["code"])
		self.message = response.json["errors"][0]["message"]
	
	def __str__(self):
		return self.message


class VermillionClient:
	def __init__(self, device_id=None):
		self.device_id = device_id
		
		self.request_callback = http.request
		
		ca = resources.certificate("Nintendo_Class_2_CA_G3.der")
		self.context = tls.TLSContext()
		self.context.set_authority(ca)
		
		self.host = "gw.hac.lp1.vermillion.srv.nintendo.net"
		
		self.system_version = LATEST_VERSION
		self.user_agent = USER_AGENT %(common.FIRMWARE_VERSIONS[LATEST_VERSION], self.device_id)
		self.api_version = API_VERSION[self.system_version]
	
	def set_request_callback(self, callback): self.request_callback = callback
	
	def set_context(self, context): self.context = context
	def set_certificate(self, cert, key): self.context.set_certificate(cert, key)
	
	def set_host(self, host):
		self.host = host
	
	def set_system_version(self, version):
		if version not in common.FIRMWARE_VERSIONS:
			raise ValueError("Unknown system version: %i" %version)
		
		self.system_version = version
		self.user_agent = USER_AGENT %(common.FIRMWARE_VERSIONS[LATEST_VERSION], self.device_id)
		self.api_version = API_VERSION[self.system_version]
	
	async def request(self, req, host, *, device_token=None, accounts_token=None):
		if self.user_agent_nim is None:
			raise ValueError("This request requires a device id")
		
		req.headers["Host"] = host
		req.headers["Accept"] = "*/*"
		req.headers["User-Agent"] = self.user_agent
		if accounts_token is not None: # Obtained from https://accounts.nintendo.com/connect/1.0.0/authorize
			req.headers["X-Nintendo-Account-Authorization"] = "Bearer " + accounts_token
		if device_token is not None: # CLIENT_ID_DRAGONS
			req.headers["X-Nintendo-Device-Authorization"] = "Bearer " + device_token
		if req.json is not None:
			req.headers["Content-Type"] = "application/json"
			req.headers["Content-Length"] = 0
		
		response = await self.request_callback(host, req, self.context)
		if response.error() and response.json:
			logger.error("Vermillion server returned an error: %s" %response.json)
			raise VermillionError(response)
		response.raise_if_error()
		return response
	
	async def put_penne_id(self, device_token, penne_id):
		req = http.HTTPRequest.put("/v%i/devices/penne-id" %self.api_version)
		req.json = {
			"penneId": penne_id,
		}
		
		await self.request(req, self.host, device_token=device_token)
	
	async def request_vermillion_device_id(self, device_token):
		req = http.HTTPRequest.get("/v%i/devices/vermillion-device-id" %self.api_version)
		response = await self.request(req, self.host, device_token=device_token)
		return response.json

	async def request_accounts_config(self, device_token, accounts_token):
		req = http.HTTPRequest.get("/v%i/accounts/config" %self.api_version)
		response = await self.request(req, self.host, device_token=device_token, accounts_token=accounts_token)
		return response.json