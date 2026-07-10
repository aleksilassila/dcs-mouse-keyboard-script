# Aleksi's DCS Script v1.0

if starting:
	import math
	system.setThreadTiming(TimingTypes.HighresSystemTimer)
	system.threadExecutionInterval = 20

	tick = 0

	freelook_toggle = True
	k_toggle = False
	control_mode = 1
	axis_max = float(vJoy[0].axisMax)

	def linear_map(value, x_min, x_max, y_min, y_max):
		return y_min + (value - x_min) * (y_max - y_min) / (x_max - x_min)
	
	class VirtualAxis:
		def __init__(self, axis_max, sensitivity=1.0, trim_value=None, linear_rate=0.0, constant_rate=0.0, invert_linear_curve=False):
			self.value = 0.0
			self.trim_value = trim_value
			self.axis_max = float(axis_max)
			self.sensitivity = sensitivity
			self.linear_rate = linear_rate
			self.constant_rate = constant_rate
			self.invert_linear_curve = invert_linear_curve
			self.did_move = False

		def move(self, delta):
			trim_diff = (self.trim_value - self.value) if self.trim_value is not None else 0

			constant_component = self.constant_rate * (1 if trim_diff > 0 else -1) if self.constant_rate != 0 else 0
			linear_component = trim_diff * self.linear_rate if not self.invert_linear_curve else (axis_max - abs(trim_diff)) * self.linear_rate if trim_diff > 0 else (axis_max - abs(trim_diff)) * self.linear_rate * -1 if trim_diff < 0 else 0

			self.value = self.value + delta * self.sensitivity + min(abs(trim_diff), max(-abs(trim_diff), linear_component + constant_component))
			self.did_move = True

			self.clamp()

		def set_trim(self, new_trim=None):
			self.trim_value = new_trim
			self.clamp()

		def offset_trim(self, delta):
			if self.trim_value is None:
				self.trim_value = 0.0
			self.trim_value += delta
			self.value += delta
			self.clamp()

		def set_val(self, val):
			self.value = val
			self.clamp()

		def clamp(self):
			if self.value > self.axis_max:
				self.value = self.axis_max
			elif self.value < -self.axis_max:
				self.value = -self.axis_max

			if self.trim_value is not None and self.trim_value > self.axis_max:
				self.trim_value = self.axis_max
			elif self.trim_value is not None and self.trim_value < -self.axis_max:
				self.trim_value = -self.axis_max

		def post_update(self):
			if not self.did_move:
				self.move(0)
			self.did_move = False

	class VirtualJoystick:
		def __init__(self):
			self.value_x = 0
			self.value_y = 0

			self.axis_x = VirtualAxis(axis_max, sensitivity=8, linear_rate=0.015, constant_rate=15, trim_value=0.0)
			self.axis_y = VirtualAxis(axis_max, sensitivity=8, linear_rate=0.015, constant_rate=15)

			# self.centered_axis_x = VirtualAxis(axis_max, sensitivity=8, linear_rate=0.015, constant_rate=15, trim_value=0.0)
			self.centered_axis_y = VirtualAxis(axis_max, sensitivity=8, linear_rate=0.015, constant_rate=15, trim_value=0.0)

			self.lerp_ticks = 25
			self.cumulative_delta_threshold = 25

			self.lerp_tick = 0
			self.cumulative_delta = 0

			self.was_centered = False

		def update(self, deltaX, deltaY, centered=False):
			centered = centered or (self.cumulative_delta < self.cumulative_delta_threshold and (abs(self.value_x) > 1 or abs(self.value_y) > 1))

			# On center press
			if centered and not self.was_centered:
				self.lerp_tick = tick
				self.cumulative_delta = 0
				# self.centered_axis_x.set_val(0)
				self.centered_axis_y.set_val(0)

			# On center release
			if self.was_centered and not centered:
				# self.axis_x.set_val(self.value_x)
				self.axis_y.set_val(self.value_y)

			if centered:
				self.cumulative_delta += abs(deltaX) + abs(deltaY)
				# self.centered_axis_x.move(deltaX)
				self.centered_axis_y.move(deltaY)
			else:
				# self.axis_x.move(deltaX)
				self.axis_y.move(deltaY)

			self.axis_x.move(deltaX)

			lerp_progress = min(1, (tick - self.lerp_tick) / float(self.lerp_ticks)) if centered else 0
			# self.value_x = self.centered_axis_x.value * lerp_progress + self.axis_x.value * (1 - lerp_progress)
			self.value_x = self.axis_x.value
			self.value_y = self.centered_axis_y.value * lerp_progress + self.axis_y.value * (1 - lerp_progress)

			self.was_centered = centered

		def post_update(self):
			self.axis_x.post_update()
			self.axis_y.post_update()
			# self.centered_axis_x.post_update()
			self.centered_axis_y.post_update()

	class VirtualButtonAxis:
		def __init__(self, decay=1, max_val=15):
			self.decay = decay
			self.value = 0.0
			self.max_val = max_val

		def clamp(self):
			if self.value > self.max_val:
				self.value = self.max_val
			elif self.value < -self.max_val:
				self.value = -self.max_val

		def move(self, delta):
			self.value += delta
			self.clamp()
				
		@property
		def increment(self):
			return self.value > 0
		
		@property
		def decrement(self):
			return self.value < 0

		def post_update(self):
			if self.value > 0:
				self.value = max(0, self.value - self.decay)
			elif self.value < 0:
				self.value = min(0, self.value + self.decay)

	class VirtualButton:
		def __init__(self):
			self.pressed = False
			self.released = False
			self.pressed_since = 0
			self.on_down = False
			self.on_up = False

		def update(self, pressed = False):
			self.on_down = pressed and not self.pressed
			self.on_up = not pressed and self.pressed

			if self.released:
				self.released = False
				# self.pressed_since = 0

			if pressed and not self.pressed:
				self.pressed_since = tick
			elif not pressed and self.pressed:
				# self.pressed_since = 0
				self.released = True

			self.pressed = pressed

		def on_press(self):
			return self.on_down
		
		def on_release(self):
			return self.on_up

	class VirtualKeys:
		def __init__(self):
			self.keys = [Key.__dict__[name] for name in Key.__dict__ if isinstance(Key.__dict__[name], Key)]

			self.held = {}			# currently down
			self.on_down = {}		# went down this tick
			self.on_up = {}			# went up this tick
			self.pressed_since = {}	# tick the current press started
			self.held_with = {}		# keys that were down at the moment of press

			for key in self.keys:
				self.held[key] = False
				self.on_down[key] = False
				self.on_up[key] = False
				self.pressed_since[key] = 0
				self.held_with[key] = set()

		def update(self, freelook=False):
			# Read the whole keyboard once so held_with sees a consistent snapshot
			current = {}
			for key in self.keys:
				current[key] = keyboard.getKeyDown(key) and not freelook

			for key in self.keys:
				down = current[key]
				was = self.held[key]

				self.on_down[key] = down and not was
				self.on_up[key] = not down and was

				if self.on_down[key]:
					self.pressed_since[key] = tick
					self.held_with[key] = set(other for other in self.keys if other != key and current[other])

				self.held[key] = down

		def on_press(self, key, with_mods=[], without_mods=[]):
			held = self.held_with.get(key, set())
			valid_with_mods = all(mod in held for mod in with_mods)
			valid_without_mods = all(mod not in held for mod in without_mods)

			return self.on_down.get(key, False) and valid_with_mods and valid_without_mods

		def on_release(self, key, with_mods=[], without_mods=[]):
			held = self.held_with.get(key, set())
			valid_with_mods = all(mod in held for mod in with_mods)
			valid_without_mods = all(mod not in held for mod in without_mods)

			return self.on_up.get(key, False) and valid_with_mods and valid_without_mods

		def is_pressed(self, key, with_mods=[], without_mods=[]):
			held = self.held_with.get(key, set())
			valid_with_mods = all(mod in held for mod in with_mods)
			valid_without_mods = all(mod not in held for mod in without_mods)

			return self.held.get(key, False) and valid_with_mods and valid_without_mods

	class DCSProfile(object):
		def __init__(self):
			self.axis = []

		def post_update(self):
			for axis in self.axis:
				axis.post_update()

			diagnostics.watch(vJoy[0].x)
			diagnostics.watch(vJoy[0].y)
			diagnostics.watch(vJoy[0].z)
			diagnostics.watch(vJoy[0].rx)
			diagnostics.watch(vJoy[0].ry)
			diagnostics.watch(vJoy[0].rz)
			diagnostics.watch(vJoy[1].x)
			diagnostics.watch(vJoy[1].y)
			diagnostics.watch(vJoy[1].z)
			diagnostics.watch(vJoy[1].rx)
			diagnostics.watch(vJoy[1].ry)
			diagnostics.watch(vJoy[1].rz)


	class AirplaneProfile(DCSProfile):
		def __init__(self):
			self.pitch_sensitivity = 8
			self.pitch_linear_rate = 0.015
			self.pitch_constant_rate = 25
			self.roll_sensitivity = 8
			self.roll_linear_rate = 0.015
			self.roll_constant_rate = 25
			self.brakes_multiplier = 1
			self.pedals_sensitivity = 1

			# Sticky mouse 4
			self.was_mouse5_pressed = False
			self.hold_mouse5_until = 0

			self.mouse5 = VirtualButton()
			self.f = VirtualButton()

			self.z = VirtualButton()
			self.x = VirtualButton()
			self.c = VirtualButton()

		def setup(self):
			# self.axis_pitch = VirtualAxis(axis_max, sensitivity=8, linear_rate=0.015, constant_rate=15)
			# self.axis_roll = VirtualAxis(axis_max, sensitivity=8, linear_rate=0.015, constant_rate=15, trim_value=0.0)
			self.joystick = VirtualJoystick()
			
			self.pedal_speed = VirtualAxis(1.0, sensitivity=0.1, constant_rate=0.1)
			self.axis_pedal = VirtualAxis(axis_max, sensitivity=200, linear_rate=0.015, constant_rate=20)
			
			self.axis_throttle = VirtualAxis(axis_max, sensitivity=200)
			self.axis_throttle.set_val(axis_max)
			
			self.axis_brake_left = VirtualAxis(axis_max, sensitivity=600, constant_rate=600)
			self.axis_brake_left.set_val(axis_max)
			self.axis_brake_left.set_trim(axis_max)
			
			self.axis_brake_right = VirtualAxis(axis_max, sensitivity=600, constant_rate=600)
			self.axis_brake_right.set_val(axis_max)
			self.axis_brake_right.set_trim(axis_max)

			self.axis_zoom = VirtualAxis(axis_max, sensitivity=-20)
			self.axis_zoom_out = VirtualAxis(axis_max, constant_rate=400, linear_rate=0.5, trim_value=self.axis_zoom.value)
			# self.axis_manual_zoom = VirtualButtonAxis(decay=20, max_val=1000)
			self.axis_manual_zoom = VirtualAxis(axis_max, sensitivity=20)
			
			self.axis = [self.joystick, self.pedal_speed, self.axis_pedal, self.axis_throttle, self.axis_brake_left, self.axis_brake_right, self.axis_zoom, self.axis_zoom_out, self.axis_manual_zoom]

		def update(self, freelook=False, control_layer=False, alt_pressed=False, shift_pressed=False, control_mode=1, active_layer_offset=0):
			deltaX = mouse.deltaX
			deltaY = mouse.deltaY

			self.mouse5.update(pressed = (mouse.getButton(4) and not freelook))
			self.f.update(pressed = (virtual_keys.is_pressed(Key.F, without_mods=mod_keys) and not freelook))
			self.z.update(pressed = keyboard.getKeyDown(Key.Z) and not freelook)
			self.x.update(pressed = keyboard.getKeyDown(Key.X) and not freelook)
			self.c.update(pressed = keyboard.getKeyDown(Key.C) and not freelook)

			self.joystick.update(deltaX if (control_mode == 1 and not freelook) else 0, deltaY if (control_mode == 1 and not freelook) else 0, centered=(mouse.getButton(4) or (control_mode == 2 and not freelook)))

			if not freelook:
				# trim_pressed = tick < self.mouse5.pressed_since + 50 or self.mouse5.pressed # 1000ms after release
				trim_pressed = mouse.getButton(4) and not freelook

				f_held = False
				f_pressed = False
				shift_f_pressed = False

				if shift_pressed:
					shift_f_pressed = self.f.released
				else:
					f_held = self.f.pressed and tick > self.f.pressed_since + 25
					f_pressed = self.f.released and tick < self.f.pressed_since + 25
	
				# mouse axis
				if control_mode == 1:
					# self.axis_pitch.set_trim(0 if trim_pressed else None)
					if f_held:
						# self.axis_roll.set_trim(self.axis_roll.value)
						self.joystick.axis_x.set_trim(self.joystick.axis_x.value)
					# self.axis_roll.move(deltaX)
					# self.axis_pitch.move(-deltaY)
					pass
				elif control_mode == 2:
					# self.axis_pitch.set_trim(0)
					self.axis_pedal.set_trim(0 if trim_pressed else None)
					self.axis_pedal.move(deltaX / 50 * self.pedals_sensitivity)

				# Trims
				if keyboard.getKeyDown(Key.LeftShift):
					if self.z.on_press():
						self.axis_pedal.set_trim(self.axis_pedal.value)
					elif self.x.on_press():
						self.joystick.axis_x.set_trim(self.joystick.axis_x.value)
					elif self.c.on_press():
						self.joystick.centered_axis_y.set_trim(self.joystick.value_y)
				elif keyboard.getKeyDown(Key.LeftControl):
					if keyboard.getKeyDown(Key.Z):
						self.axis_pedal.set_trim(0)
					elif keyboard.getKeyDown(Key.X):
						self.joystick.axis_x.set_trim(0)
					elif keyboard.getKeyDown(Key.C):
						self.joystick.centered_axis_y.set_trim(0)

				# Scroll wheel
				if mouse.getPressed(2): # MOUSE 3
					if self.axis_zoom.value < 6000 and self.axis_zoom.value > 2000:
						self.axis_zoom.set_val(-11000)
					else:
						self.axis_zoom.set_val(5000)
				elif mouse.wheel != 0:
					if keyboard.getKeyDown(Key.LeftShift):
						self.axis_manual_zoom.move(mouse.wheel)
					else:
						self.axis_zoom.move(mouse.wheel)

				# throttle control
				if virtual_keys.on_press(Key.W, without_mods=layer_triggers) and shift_pressed:
					self.axis_throttle.set_val((math.ceil(round((self.axis_throttle.value + axis_max) / (axis_max * 2) * 4, 6)) - 1) * (axis_max * 2) / 4 - axis_max)
				elif virtual_keys.is_pressed(Key.W, without_mods=layer_triggers) and not shift_pressed:
					self.axis_throttle.move(-1)
				if virtual_keys.on_press(Key.S, without_mods=layer_triggers) and shift_pressed:
					self.axis_throttle.set_val((math.floor(round((self.axis_throttle.value + axis_max) / (axis_max * 2) * 4, 6)) + 1) * (axis_max * 2) / 4 - axis_max)
				elif virtual_keys.is_pressed(Key.S, without_mods=layer_triggers) and not shift_pressed:
					self.axis_throttle.move(1)
				
				# pedal control
				if virtual_keys.is_pressed(Key.Q, without_mods=layer_triggers):
					self.axis_brake_left.move(-2)
				if virtual_keys.is_pressed(Key.E, without_mods=layer_triggers):
					self.axis_brake_right.move(-2)
				
				if virtual_keys.is_pressed(Key.A, without_mods=layer_triggers):
					if shift_pressed:
						# self.axis_roll.offset_trim(-10)
						self.joystick.axis_x.offset_trim(-10)
					else:
						self.axis_pedal.offset_trim(-self.axis_pedal.sensitivity * self.pedal_speed.value)
						self.pedal_speed.move(1)
				if virtual_keys.is_pressed(Key.D, without_mods=layer_triggers):
					if shift_pressed:
						# self.axis_roll.offset_trim(10)
						self.joystick.axis_x.offset_trim(10)
					else:
						self.axis_pedal.offset_trim(self.axis_pedal.sensitivity * self.pedal_speed.value)
						self.pedal_speed.move(1)
				if shift_f_pressed:
					# self.axis_roll.set_trim(0)
					self.joystick.axis_x.set_trim(0)
				elif f_pressed:
					self.axis_pedal.set_trim(0)
				
				# if layer_keys[Key.F].was_layer_pressed(0):
				# 	if shift_pressed:
				# 		self.axis_roll.set_trim(0)
				# 	else:
				# 		self.axis_pedal.set_trim(0)

			self.axis_zoom_out.trim_value = self.axis_zoom.value

			# vJoy axis mapping
			# vJoy[0].x = self.axis_roll.value
			# vJoy[0].y = self.axis_pitch.value
			vJoy[0].x = self.joystick.value_x
			# vJoy[0].y = linear_map(self.joystick.value_y, 0, axis_max, axis_max / 2.5, axis_max) if self.joystick.value_y >= 0 else linear_map(self.joystick.value_y, -axis_max, 0, -axis_max, axis_max / 2.5)
			# vJoy[0].y = linear_map(self.joystick.value_y, 0, axis_max, axis_max / 1.93, axis_max) if self.joystick.value_y >= 0 else linear_map(self.joystick.value_y, -axis_max, 0, -axis_max, axis_max / 1.93) # A-10C
			vJoy[0].y = self.joystick.value_y
			vJoy[0].z = self.axis_throttle.value
			vJoy[0].rx = self.axis_brake_left.value
			vJoy[0].ry = self.axis_brake_right.value
			vJoy[0].rz = self.axis_pedal.value
			vJoy[0].slider = linear_map(self.axis_zoom_out.value, -axis_max, axis_max, -axis_max, 11000)
			#vJoy[0].slider = self.axis_zoom_out.value
			vJoy[1].slider = self.axis_manual_zoom.value
			# vJoy[0].setButton(29, self.axis_manual_zoom.increment)
			# vJoy[0].setButton(30, self.axis_manual_zoom.decrement)

			# diagnostics.watch(self.axis_manual_zoom.value)
			# diagnostics.watch(self.axis_manual_zoom.increment)
			# diagnostics.watch(self.axis_manual_zoom.decrement)

			diagnostics.watch(vJoy[0].slider)
			# diagnostics.watch(self.axis_pitch.value)
			# diagnostics.watch(self.axis_pitch.trim_value)
			diagnostics.watch(self.pedal_speed.value)

			self.post_update()

	class F16CProfile(AirplaneProfile):
		def __init__(self):
			super(F16CProfile, self).__init__()
			self.pitch_sensitivity = 8
			self.pitch_linear_rate = 100
			self.roll_sensitivity = 8
			self.roll_linear_rate = 100
			self.brakes_multiplier = 1
			self.pedals_sensitivity = 1 / (45/45)

			# Afterburner Z = -8429 = 24.273% / 75.726%

	class A10CProfile(AirplaneProfile):
		def __init__(self):
			super(A10CProfile, self).__init__()
			self.pitch_sensitivity = 8
			self.pitch_linear_rate = 100
			self.roll_sensitivity = 8
			self.roll_linear_rate = 100
			self.brakes_multiplier = 1
			self.pedals_sensitivity = 1 / (80/45)

	class A4ECProfile(AirplaneProfile):
		def __init__(self):
			super(A4ECProfile, self).__init__()
			self.pitch_sensitivity = 13
			self.pitch_linear_rate = 0.03
			self.roll_sensitivity = 4
			self.roll_linear_rate = 0.015
			self.brakes_multiplier = -1

	class HelicopterProfile(DCSProfile):
		def __init__(self):
			self.pedal_sensitivity = 200
			self.pitch_linear_rate = 0.03
			self.roll_linear_rate = 0.0075
			self.always_trim_everything = False

		def setup(self):
			self.axis_pitch = VirtualAxis(axis_max, sensitivity=3, linear_rate=self.pitch_linear_rate, trim_value=0.0)
			self.axis_roll = VirtualAxis(axis_max, sensitivity=3, linear_rate=self.roll_linear_rate, trim_value=0.0)
			self.axis_pedal = VirtualAxis(axis_max, sensitivity=self.pedal_sensitivity, linear_rate=0.02)
			
			self.throttle_speed = VirtualAxis(1.0, sensitivity=0.025, linear_rate=0.07)
			self.throttle_speed.set_trim(0.5)
			self.throttle_speed.set_val(0.5)
			self.axis_throttle1 = VirtualAxis(axis_max, sensitivity=200)
			self.axis_throttle1.set_val(axis_max)

			self.axis_throttle2 = VirtualAxis(axis_max, sensitivity=200, linear_rate=1)
			self.axis_throttle2.set_val(axis_max)
			
			self.axis = [self.axis_roll, self.axis_pitch, self.axis_pedal, self.throttle_speed, self.axis_throttle1, self.axis_throttle2]

		def update(self, freelook=False, control_layer=False, alt_pressed=False, shift_pressed=False, control_mode=1, active_layer_offset=0):
			deltaX = mouse.deltaX
			deltaY = mouse.deltaY

			if not freelook:
				# mouse axis
				if deltaX:
					self.axis_roll.move(deltaX)

				if deltaY:
					self.axis_pitch.move(-deltaY)

				if mouse.wheel != 0:
					self.axis_pedal.offset_trim(mouse.wheel * self.axis_pedal.sensitivity / 60)

				self.axis_pitch.set_trim(0 if mouse.getButton(4) else None)
				self.axis_roll.set_trim(0 if not self.always_trim_everything else 0 if mouse.getButton(4) else None)
				if self.always_trim_everything:
					self.axis_pedal.set_trim(0 if mouse.getButton(4) else None)

				# Y axis trim logic
				# if not self.always_trim_everything:
				# 	self.axis_pitch.set_trim()
				# if mouse.getButton(4): # MOUSE 5
				# 	self.axis_pitch.set_trim(0)
				
				if keyboard.getKeyDown(Key.Z):
					# secondary throttle control
					if keyboard.getKeyDown(Key.W):
						self.axis_throttle2.set_trim(-axis_max)
					if keyboard.getKeyDown(Key.S):
						self.axis_throttle2.set_trim(axis_max)

					vJoy[0].setButton(11, keyboard.getKeyDown(Key.A))
					vJoy[0].setButton(12, keyboard.getKeyDown(Key.D))
					vJoy[0].setButton(13, keyboard.getKeyDown(Key.Q))
					vJoy[0].setButton(14, keyboard.getKeyDown(Key.E))
				else:
					vJoy[0].setButton(11, False)
					vJoy[0].setButton(12, False)
					vJoy[0].setButton(13, False)
					vJoy[0].setButton(14, False)

					# throttle control
					if keyboard.getKeyDown(Key.W):
						self.axis_throttle1.move(-1 * self.throttle_speed.value)
						self.throttle_speed.move(1)
					if keyboard.getKeyDown(Key.S):
						self.axis_throttle1.move(1 * self.throttle_speed.value)
						self.throttle_speed.move(1)
					
					# # secondary throttle control
					# if keyboard.getKeyDown(Key.X):
					# 	self.axis_throttle2.move(-1)
					# if keyboard.getKeyDown(Key.Z):
					# 	self.axis_throttle2.move(1)
					
					# pedal control
					if keyboard.getKeyDown(Key.Q):
						self.axis_pedal.move(-1)
					if keyboard.getKeyDown(Key.E):
						self.axis_pedal.move(1)

					# X/Pedal trim logic
					if keyboard.getKeyDown(Key.A):
						if shift_pressed:
							self.axis_roll.offset_trim(-50)
						else:
							self.axis_pedal.offset_trim(-self.axis_pedal.sensitivity)
					if keyboard.getKeyDown(Key.D):
						if shift_pressed:
							self.axis_roll.offset_trim(50)
						else:
							self.axis_pedal.offset_trim(self.axis_pedal.sensitivity)
					if keyboard.getKeyDown(Key.F):
						if shift_pressed:
							self.axis_roll.set_trim(0)
						else:
							self.axis_pedal.set_trim(0)

			# vJoy axis mapping
			vJoy[0].x = self.axis_roll.value
			vJoy[0].y = self.axis_pitch.value
			vJoy[0].rx = self.axis_throttle1.value
			vJoy[0].ry = self.axis_throttle2.value
			vJoy[0].rz = self.axis_pedal.value

			self.post_update()

	class UH60Profile(HelicopterProfile):
		def __init__(self):
			super(UH60Profile, self).__init__()

	class OH6AProfile(HelicopterProfile):
		def __init__(self):
			super(OH6AProfile, self).__init__()
			self.pedal_sensitivity = 350

	class UH1HProfile(HelicopterProfile):
		def __init__(self):
			super(UH1HProfile, self).__init__()
			self.always_trim_everything = True
			self.pedal_sensitivity = 350

	profiles = dict([
		("F-16C", F16CProfile()),
		("A-4E-C", A4ECProfile()),
		("UH-60L", UH60Profile()),
		("OH-6A", OH6AProfile()),
		("UH-1H", UH1HProfile()),
	])

	for profile in profiles.values():
		profile.setup()

	active_profile = None

	virtual_keys = VirtualKeys()

	mod_keys = [
		Key.Z,
		Key.X,
		Key.C,
		Key.V,
		Key.LeftShift,
		Key.RightShift,
		Key.LeftControl,
		Key.RightControl,
	]

	layer_triggers = [
		Key.Z,
		Key.X,
		Key.C,
		Key.V
	]

	layer_keys = [
		(Key.W, 0),
		(Key.S, 1),
		(Key.A, 2),
		(Key.D, 3),
		(Key.Q, 4),
		(Key.E, 5),
		(Key.F, 6),
		(Key.R, 7),
		# (Key.G, 8),
		# (Key.T, 9),
		(Key.D1, 10),
		(Key.D2, 11),
		(Key.D3, 12),
		(Key.D4, 13),
		(Key.D5, 14),
		(Key.D6, 15),
		(Key.D7, 16),	
		(Key.D8, 17),
		(Key.D9, 18),
		(Key.D0, 19)
	]

	active_layer_offset = 0

# Alt
alt_pressed = keyboard.getKeyDown(Key.LeftAlt) or keyboard.getKeyDown(Key.RightAlt)
shift_pressed = keyboard.getKeyDown(Key.LeftShift) or keyboard.getKeyDown(Key.RightShift)

# Freelook / Control mode toggle
if mouse.getPressed(3):
	if not freelook_toggle:
		vJoy[0].setPressed(29)
	freelook_toggle = True
elif keyboard.getPressed(Key.Grave):
	if freelook_toggle:
		vJoy[0].setPressed(29)
	else:
		control_mode = 1
	freelook_toggle = False
elif keyboard.getPressed(Key.R) and not freelook_toggle:
	control_mode = 2

control_layer = not keyboard.getKeyDown(Key.Z) and not keyboard.getKeyDown(Key.X) and not keyboard.getKeyDown(Key.C) and not keyboard.getKeyDown(Key.V)
freelook = alt_pressed or freelook_toggle

# K Toggle
if keyboard.getPressed(Key.K):
	k_toggle = not k_toggle

if k_toggle:
	# K Binds
	if keyboard.getKeyDown(Key.D1):
		active_profile = profiles["UH-60L"]

	if keyboard.getPressed(Key.D2):
		active_profile = profiles["OH-6A"]

	if keyboard.getKeyDown(Key.D3):
		active_profile = profiles["UH-1H"]

	if keyboard.getKeyDown(Key.D4):
		active_profile = profiles["A-4E-C"]

	if keyboard.getKeyDown(Key.D5):
		active_profile = profiles["F-16C"]

	# Match any keypress
	for key in Key.__dict__:
		#diagnostics.debug(key)
		#diagnostics.debug(isinstance(Key.__dict__[key], Key))
		
		if not isinstance(Key.__dict__[key], Key):
			continue

		if keyboard.getPressed(Key.__dict__[key]):
			diagnostics.debug(Key.__dict__[key])
			k_toggle = False
			break

virtual_keys.update(freelook=(freelook or k_toggle))

# Layers
for (key, offset) in layer_keys:
	vJoy[0].setButton(0 + offset, not (freelook or k_toggle) and virtual_keys.is_pressed(key, without_mods=mod_keys))

for (key, offset) in layer_keys:
	vJoy[0].setButton(40 + offset, not (freelook or k_toggle) and virtual_keys.is_pressed(key, with_mods=[Key.Z], without_mods=[Key.X, Key.C, Key.V]))

for (key, offset) in layer_keys:
	vJoy[0].setButton(60 + offset, not (freelook or k_toggle) and virtual_keys.is_pressed(key, with_mods=[Key.X], without_mods=[Key.Z, Key.C, Key.V]))

for (key, offset) in layer_keys:
	vJoy[0].setButton(80 + offset, not (freelook or k_toggle) and virtual_keys.is_pressed(key, with_mods=[Key.C], without_mods=[Key.Z, Key.X, Key.V]))

for (key, offset) in layer_keys:
	vJoy[0].setButton(100 + offset, not (freelook or k_toggle) and virtual_keys.is_pressed(key, with_mods=[Key.V], without_mods=[Key.Z, Key.X, Key.C]))

if active_profile is not None:
	active_profile.update(freelook=freelook, alt_pressed=alt_pressed, shift_pressed=shift_pressed, control_layer=control_layer, control_mode=control_mode, active_layer_offset=active_layer_offset)

if not freelook and not k_toggle:
	vJoy[0].setButton(20, mouse.getButton(0)) # MOUSE 1
	vJoy[0].setButton(21, mouse.getButton(1)) # MOUSE 2

diagnostics.watch(k_toggle)
diagnostics.watch(freelook)
diagnostics.watch(control_layer)
diagnostics.watch(active_profile.__class__.__name__ if active_profile else None)
diagnostics.watch(active_layer_offset)
tick += 1
