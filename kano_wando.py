# name='kano_wando'
# description='Python module for interfacing with the Kano wand'
# author='Jesse Lieberg (@GammaGames) - Linux Platform'
# adapter='Jacob New' (@newpvisuals) - Windows Adaptation'
# url='https://github.com/GammaGames/kano_wand'

from enum import Enum
from bleak import BleakClient
from bleak import BleakScanner
import inspect
import numpy
import threading
import uuid
import asyncio


from time import sleep

class _INFO(Enum):
	"""Enum containing info UUIDs"""
	SERVICE 			= '64A70010-F691-4B93-A6F4-0968F5B648F8'
	ORGANIZATION_CHAR 	= '64A7000B-F691-4B93-A6F4-0968F5B648F8'
	SOFTWARE_CHAR 		= '64A70013-F691-4B93-A6F4-0968F5B648F8'
	HARDWARE_CHAR 		= '64A70001-F691-4B93-A6F4-0968F5B648F8'

class _IO(Enum):
	"""Enum containing _IO UUIDs"""
	SERVICE 			= '64A70012-F691-4B93-A6F4-0968F5B648F8'
	BATTERY_CHAR 		= '64A70007-F691-4B93-A6F4-0968F5B648F8'
	USER_BUTTON_CHAR 	= '64A7000D-F691-4B93-A6F4-0968F5B648F8'
	VIBRATOR_CHAR		= '64A70008-F691-4B93-A6F4-0968F5B648F8'
	LED_CHAR 			= '64A70009-F691-4B93-A6F4-0968F5B648F8'
	KEEP_ALIVE_CHAR 	= '64A7000F-F691-4B93-A6F4-0968F5B648F8'

class _SENSOR(Enum):
	"""Enum containing sensor UUIDs"""
	SERVICE 			= '64A70011-F691-4B93-A6F4-0968F5B648F8'
	TEMP_CHAR			= '64A70014-F691-4B93-A6F4-0968F5B648F8'
	QUATERNIONS_CHAR 	= '64A70002-F691-4B93-A6F4-0968F5B648F8'
	# RAW_CHAR			= '64A7000A-F691-4B93-A6F4-0968F5B648F8'
	# MOTION_CHAR 		= '64A7000C-F691-4B93-A6F4-0968F5B648F8'
	MAGN_CALIBRATE_CHAR = '64A70021-F691-4B93-A6F4-0968F5B648F8'
	QUATERNIONS_RESET_CHAR = '64A70004-F691-4B93-A6F4-0968F5B648F8'

class PATTERN(Enum):
	"""Enum for wand vibration patterns"""
	REGULAR = 1
	SHORT = 2
	BURST = 3
	LONG = 4
	SHORT_LONG = 5
	SHORT_SHORT = 6
	BIG_PAUSE = 7

class Wand():
	"""A wand class to interact with the Kano wand
	"""

	def __init__(self, device, debug=False):
		"""Create a new wand
		Arguments:
			device {bluepy.ScanEntry} -- Device information
		Keyword Arguments:
			debug {bool} -- Print debug messages (default: {False})
		"""
		super().__init__(None)
		# Meta stuff
		self.debug = debug
		self._dev = device
		self.name = device.name
		self.client = BleakClient(self._dev)
		
		if debug:
			print("Wand: {}\n\rWand Mac: {}".format(self.name, device.addr))

		# Notification stuff
		self.connected = False
		self._position_callbacks = {}
		self._position_subscribed = False
		self._button_callbacks = {}
		self._button_subscribed = False
		self._temperature_callbacks = {}
		self._temperature_subscribed = False
		self._battery_callbacks = {}
		self._battery_subscribed = False
		self._notification_thread = None
		self._position_notification_handle = 41
		self._button_notification_handle = 33
		self._temp_notification_handle = 56
		self._battery_notification_handle = 23


	async def connect(self):
		if self.debug:
			print("Connecting to {}...".format(self.name))

		self.client = BleakClient(self._dev)
		await self.client.connect()
		self.connected = await self.client.is_connected()


		self.post_connect()

		if self.debug:
			print("Connected to {}".format(self.name))


	def post_connect(self):
		"""Do anything necessary after connecting
		"""
		pass

	async def disconnect(self):
		await self.client.disconnect()
		self.connected = False
		self._position_subscribed = False
		self._button_subscribed = False
		self._temperature_subscribed = False
		self._battery_subscribed = False

		self.post_disconnect()

		if self.debug:
			print("Disconnected from {}".format(self.name))

	def post_disconnect(self):
		"""Do anything necessary after disconnecting
		"""
		pass


	async def get_organization(self):
		"""Get organization of device
		Returns {str} -- Organization name
		"""
		if not hasattr(self, "_organization"):
			self._organization = await self.client.read_gatt_char(_INFO.ORGANIZATION_CHAR.value)

		return self._organization.decode("utf-8")


	async def get_software_version(self):
		"""Get software version
		Returns {str} -- Version number
		"""
		if not hasattr(self, "_software"):
			self._software = await self.client.read_gatt_char(_INFO.SOFTWARE_CHAR.value)[0]

		return self._software.decode("utf-8")


	async def get_hardware_version(self):
		"""Get hardware version
		Returns {str} -- Hardware version
		"""
		if not hasattr(self, "_hardware"):
			self._hardware = await self.client.read_gatt_char(_INFO.HARDWARE_CHAR.value)[0]

		return self._hardware.decode("utf-8")
	
	
	async def get_battery(self):
		"""Get battery level (currently only returns 0)
		Returns {str} -- Battery level
		"""
		if not hasattr(self, "_battery"):
			self._battery = await self.client.read_gatt_char(_IO.BATTERY_CHAR.value)[0]

		return self._battery.decode("utf-8")


	async def get_button(self):
		"""Get current button status
		Returns {bool} -- Button pressed status
		"""
		if not hasattr(self, "_button"):
			self._button = await self.client.read_gatt_char(_IO.USER_BUTTON_CHAR.value)[0]

		return self._button[0] == 1


	async def get_temperature(self):
		"""Get temperature
		Returns {str} -- Battery level
		"""
		if not hasattr(self, "_temperature"):
			self._temperature = await self.client.read_gatt_char(_SENSOR.TEMP_CHAR.value)[0]

		return self._temperature.decode("utf-8")
	
	
	async def keep_alive(self):
		"""Keep the wand's connection active
		Returns {bytes} -- Status
		"""
		# Is not documented because it doesn't seem to work?
		if self.debug:
			print("Keeping wand alive.")

		if not hasattr(self, "_alive"):
			self._alive = _IO.KEEP_ALIVE_CHAR.value
		return await self.client.write_gatt_char(self._alive, bytes([1]))
		
		
	async def vibrate(self, pattern=PATTERN.REGULAR):
		"""Vibrate wand with pattern
		Keyword Arguments:
			pattern {kano_wand.PATTERN} -- Vibration pattern (default: {PATTERN.REGULAR})
		Returns {bytes} -- Status
		"""
		if isinstance(pattern, PATTERN):
			message = [pattern.value]
		else:
			message = [pattern]
	
		if self.debug:
			print("Setting LED to {}".format(message))
	
		if not hasattr(self, "_vibrator"):
			self._vibrator = _IO.VIBRATOR_CHAR.value
		return await self.client.write_gatt_char(self._vibrator, bytes(message))


	async def set_led(self, color="0x2185d0", on=True):
		"""Set the LED's color
		Keyword Arguments:
			color {str} -- Color hex code (default: {"0x2185d0"})
			on {bool} -- Whether light is on or off (default: {True})
		Returns {bytes} -- Status
		"""
		message = []
		if on:
			message.append(1)
		else:
			message.append(0)
	
		# I got this from Kano's node module
		color = int(color.replace("#", ""), 16)
		r = (color >> 16) & 255
		g = (color >> 8) & 255
		b = color & 255
		rgb = (((r & 248) << 8) + ((g & 252) << 3) + ((b & 248) >> 3))
		message.append(rgb >> 8)
		message.append(rgb & 0xff)
	
		if self.debug:
			print("Setting LED to {}".format(message))
	
		if not hasattr(self, "_led"):
			self._led = _IO.LED_CHAR.value
		return await self.client.write_gatt_char(self._led, bytes(message))
	
	
		


	# SENSORS
	async def on(self, event, callback):
		"""Add an event listener
		Arguments:
			event {str} -- Event type, "position", "button", "temp", or "battery"
			callback {function} -- Callback function
		Returns {str} -- ID of the callback for removal later
		"""
		if self.debug:
			print("Adding callback for {} notification...".format(event))

		id = None
		if event == "position":
			id = uuid.uuid4()
			self._position_callbacks[id] = callback
			await self.client.start_notify(_SENSOR.POSITION_CHAR.value, callback)
		elif event == "button":
			id = uuid.uuid4()
			self._button_callbacks[id] = callback
			await self.client.start_notify(_IO.USER_BUTTON_CHAR.value, callback)
		elif event == "temp":
			id = uuid.uuid4()
			self._temperature_callbacks[id] = callback
			await self.client.start_notify(_SENSOR.TEMPERATURE_CHAR.value, callback)
		elif event == "battery":
			id = uuid.uuid4()
			self._battery_callbacks[id] = callback
			await self.client.start_notify(_SENSOR.BATTERY_CHAR.value, callback)

		return id

	async def off(self, uuid, continue_notifications=False):
		"""Remove a callback
		Arguments:
			uuid {str} -- Remove a callback with its id
		Keyword Arguments:
			continue_notifications {bool} -- Keep notification thread running (default: {False})
		Returns {bool} -- If removal was successful or not
		"""
		removed = False
		if self._position_callbacks.pop(uuid, None) is not None:
			removed = True
			if not continue_notifications and len(self._position_callbacks) == 0:
				await self.client.stop_notify(_SENSOR.POSITION_CHAR.value)
		elif self._button_callbacks.pop(uuid, None) is not None:
			removed = True
			if not continue_notifications and len(self._button_callbacks) == 0:
				await self.client.stop_notify(_IO.USER_BUTTON_CHAR.value)
		elif self._temperature_callbacks.pop(uuid, None) is not None:
			removed = True
			if not continue_notifications and len(self._temperature_callbacks) == 0:
				await self.client.stop_notify(_SENSOR.TEMPERATURE_CHAR.value)
		elif self._battery_callbacks.pop(uuid, None) is not None:
			removed = True
			if not continue_notifications and len(self._battery_callbacks) == 0:
				await self.client.stop_notify(_SENSOR.BATTERY_CHAR.value)

		if self.debug:
			if removed:
				print("Removed callback {}".format(uuid))
			else:
				print("Could not remove callback {}".format(uuid))

		return removed

	async def subscribe_button(self):
		await self.client.start_notify(_IO.USER_BUTTON_CHAR.value, self._on_button)

	async def unsubscribe_button(self):
		await self.client.stop_notify(_IO.USER_BUTTON_CHAR.value)

	async def subscribe_temperature(self):
		await self.client.start_notify(_SENSOR.TEMPERATURE_CHAR.value, self._on_temperature)
	
	async def unsubscribe_temperature(self):
		await self.client.stop_notify(_SENSOR.TEMPERATURE_CHAR.value)
	
	async def subscribe_battery(self):
		await self.client.start_notify(_SENSOR.BATTERY_CHAR.value, self._on_battery)
	
	async def unsubscribe_battery(self):
		await self.client.stop_notify(_SENSOR.BATTERY_CHAR.value)
	
	
	def _on_position(self, data):
		"""Private function for position notification
		Arguments:
			data {bytes} -- Data from device
		"""
		# I got part of this from Kano's node module and modified it
		y = numpy.int16(numpy.uint16(int.from_bytes(data[0:2], byteorder='little')))
		x = -1 * numpy.int16(numpy.uint16(int.from_bytes(data[2:4], byteorder='little')))
		w = -1 * numpy.int16(numpy.uint16(int.from_bytes(data[4:6], byteorder='little')))
		z = numpy.int16(numpy.uint16(int.from_bytes(data[6:8], byteorder='little')))

		if self.debug:
			pitch = "Pitch: {}".format(z).ljust(16)
			roll = "Roll: {}".format(w).ljust(16)
			print("{}{}(x, y): ({}, {})".format(pitch, roll, x, y))

		self.on_position(x, y, z, w)
		for callback in self._position_callbacks.values():
			callback(x, y, z, w)

	def on_position(self, roll, x, y, z):
		"""Function called on position notification
		Arguments:
			x {int} -- X position of wand (Between -1000 and 1000)
			y {int} -- Y position of wand (Between -1000 and 1000)
			pitch {int} -- Pitch of wand (Between -1000 and 1000)
			roll {int} -- Roll of wand (Between -1000 and 1000)
		"""
		pass

	def reset_position(self):
		"""Reset the quaternains of the wand
		"""
		handle = self._sensor_service.getCharacteristics(_SENSOR.QUATERNIONS_RESET_CHAR.value)[0].getHandle()
		with self._lock:
			self.writeCharacteristic(handle, bytes([1]))

	def _on_button(self, data):
		"""Private function for button notification
		Arguments:
			data {bytes} -- Data from device
		"""
		val = data[0] == 1

		if self.debug:
			print("Button: {}".format(val))

		self.on_button(val)
		for callback in self._button_callbacks.values():
			callback(val)

	def on_button(self, value):
		"""Function called on button notification
		Arguments:
			pressed {bool} -- If button is pressed
		"""
		pass

	def _on_temperature(self, data):
		"""Private function for temperature notification
		Arguments:
			data {bytes} -- Data from device
		"""
		val = numpy.int16(numpy.uint16(int.from_bytes(data[0:2], byteorder='little')))

		if self.debug:
			print("Temperature: {}".format(val))

		self.on_temperature(val)
		for callback in self._temperature_callbacks.values():
			callback(val)

	def on_temperature(self, value):
		"""Function called on temperature notification
		Arguments:
			value {int} -- Temperature of the wand
		"""
		pass

	def _on_battery(self, data):
		"""Private function for battery notification
		Arguments:
			data {bytes} -- Data from device
		"""
		val = data[0]

		if self.debug:
			print("Battery: {}".format(val))

		self.on_battery(val)
		for callback in self._battery_callbacks.values():
			callback(val)

	def on_battery(self, value):
		"""Function called on battery notification
		Arguments:
			value {int} -- Battery level of the wand
		"""

	def handleNotification(self, cHandle, data):
		"""Handle notifications subscribed to
		Arguments:
			cHandle {int} -- Handle of notification
			data {bytes} -- Data from device
		"""
		if cHandle == self._position_notification_handle:
			self._on_position(data)
		elif cHandle == self._button_notification_handle:
			self._on_button(data)
		elif cHandle == self._temp_notification_handle:
			self._on_temperature(data)
		elif cHandle == self._battery_notification_handle:
			self._on_battery(data)

class Shop():
	"""A scanner class to connect to wands
	"""
	def __init__(self, wand_class=Wand, debug=False):
		"""Create a new scanner
		Keyword Arguments:
			wand_class {class} -- Class to use when connecting to wand (default: {Wand})
			debug {bool} -- Print debug messages (default: {False})
		"""
		super().__init__()
		self.wand_class = wand_class
		self.debug = debug
		self._name = None
		self._prefix = None
		self._mac = None
		self._scanner = BleakScanner()

	async def scan(self, name=None, prefix="Kano-Wand", mac=None, timeout=1.0, connect=False):
		"""Scan for devices
		Keyword Arguments:
			name {str} -- Name of the device to scan for (default: {None})
			prefix {str} -- Prefix of name of device to scan for (default: {"Kano-Wand"})
			mac {str} -- MAC Address of the device to scan for (default: {None})
			timeout {float} -- Timeout before returning from scan (default: {1.0})
			connect {bool} -- Connect to the wands automatically (default: {False})
		Returns {Wand[]} -- Array of wand objects
		"""

		if self.debug:
			print("Scanning for {} seconds...".format(timeout))
		try:
			name_check = not (name is None)
			prefix_check = not (prefix is None)
			mac_check = not (mac is None)
			assert name_check or prefix_check or mac_check
		except AssertionError as e:
			print("Either a name, prefix, or mac address must be provided to find a wand")
			raise e

		if name is not None:
			self._name = name
		elif prefix is not None:
			self._prefix = prefix
		elif mac is not None:
			self._mac = mac



		## WINDOWS MODIFICATIONS  

		self.wands = []
		# Use async scanning function
		devices = await self._scanner.discover(timeout)
		for device in devices:
			self.handleDiscovery(device)
		
		##
		
		if connect:
			for wand in self.wands:
				await wand.connect()
		return self.wands


	def handleDiscovery(self, device, isNewDev, isNewData):
		"""Check if the device matches
		Arguments:
			device {bleak.backends.device} -- Device data
			isNewDev {bool} -- Whether the device is new
			isNewData {bool} -- Whether the device has already been seen
		"""

		if isNewDev:
			# Perform initial detection attempt
			mode = 0
			found = 0
			name = device.name
			if self._name is not None:
				mode += 1
				if name == self._name:
					found += 1
			if self._prefix is not None:
				mode += 1
				if name is not None and name.startswith(self._prefix):
					found += 1
			if self._mac is not None:
				mode += 1
				if device.addr == self._mac:
					found += 1

			if found >= mode:
				self.wands.append(self.wand_class(device, debug=self.debug))
			elif self.debug:
				if name != "None":
					print("Mac: {}\tCommon Name: {}".format(device.addr, name))
				else:
					print("Mac: {}".format(device.addr))
					
					
					
					
