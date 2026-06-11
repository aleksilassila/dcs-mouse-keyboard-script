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

	class LayerKey:
		def __init__(self, key, index, ignored_offsets=[0]):
			self.key = key
			self.index = index
			self.ignored_offsets = ignored_offsets
			self.active_offset = 0
			self.was_pressed = False
			self.on_down = False
			self.on_up = False
	
		def was_layer_pressed(self, active_offset):
			return self.was_pressed and self.active_offset == active_offset
		
		def on_layer_press(self, active_offset):
			return self.on_down and self.active_offset == active_offset
		
		def on_layer_release(self, active_offset):
			return self.on_up and self.active_offset == active_offset

		def update(self, active_offset, freelook=False):
			pressed = keyboard.getKeyDown(self.key) and not freelook
			self.on_down = pressed and not self.was_pressed
			self.on_up = not pressed and self.was_pressed

			if not self.was_pressed:
				self.active_offset = active_offset

			if self.active_offset not in self.ignored_offsets:
				vJoy[0].setButton(self.index + self.active_offset, pressed)

			self.was_pressed = pressed

	class VirtualKey:
		def on_press(self):
			pass

		def on_release(self):
			pass

		def is_pressed(self):
			pass

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
			self.f.update(pressed = (layer_keys[Key.F].was_layer_pressed(0) and not freelook))
			self.z.update(pressed = keyboard.getKeyDown(Key.Z) and not freelook)
			self.x.update(pressed = keyboard.getKeyDown(Key.X) and not freelook)
			self.c.update(pressed = keyboard.getKeyDown(Key.C) and not freelook)

			self.joystick.update(deltaX if (control_mode == 1 and not freelook) else 0, deltaY if (control_mode == 1 and not freelook) else 0, centered=((mouse.getButton(4) or control_mode == 2) and not freelook))

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
				if layer_keys[Key.W].on_layer_press(0) and shift_pressed:
					self.axis_throttle.set_val((math.ceil(round((self.axis_throttle.value + axis_max) / (axis_max * 2) * 5, 6)) - 1) * (axis_max * 2) / 5 - axis_max)
				elif layer_keys[Key.W].was_layer_pressed(0) and not shift_pressed:
					self.axis_throttle.move(-1)
				if layer_keys[Key.S].on_layer_press(0) and shift_pressed:
					self.axis_throttle.set_val((math.floor(round((self.axis_throttle.value + axis_max) / (axis_max * 2) * 5, 6)) + 1) * (axis_max * 2) / 5 - axis_max)
				elif layer_keys[Key.S].was_layer_pressed(0) and not shift_pressed:
					self.axis_throttle.move(1)
				
				# pedal control
				if layer_keys[Key.Q].was_layer_pressed(0):
					self.axis_brake_left.move(-2)
				if layer_keys[Key.E].was_layer_pressed(0):
					self.axis_brake_right.move(-2)
				
				if layer_keys[Key.A].was_layer_pressed(0):
					if shift_pressed:
						# self.axis_roll.offset_trim(-10)
						self.joystick.axis_x.offset_trim(-10)
					else:
						self.axis_pedal.offset_trim(-self.axis_pedal.sensitivity * self.pedal_speed.value)
						self.pedal_speed.move(1)
				if layer_keys[Key.D].was_layer_pressed(0):
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
			vJoy[0].y = linear_map(self.joystick.value_y, 0, axis_max, axis_max / 1.93, axis_max) if self.joystick.value_y >= 0 else linear_map(self.joystick.value_y, -axis_max, 0, -axis_max, axis_max / 1.93)
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

	layer_keys = {
		Key.W: LayerKey(Key.W, 0),
		Key.S: LayerKey(Key.S, 1),
		Key.A: LayerKey(Key.A, 2),
		Key.D: LayerKey(Key.D, 3),
		Key.Q: LayerKey(Key.Q, 4),
		Key.E: LayerKey(Key.E, 5),
		Key.F: LayerKey(Key.F, 6),
		Key.R: LayerKey(Key.R, 7),
		# Key.G: LayerKey(Key.G, 8),
		# Key.T: LayerKey(Key.T, 9),
		Key.D1: LayerKey(Key.D1, 10, ignored_offsets=[]),
		Key.D2: LayerKey(Key.D2, 11, ignored_offsets=[]),
		Key.D3: LayerKey(Key.D3, 12, ignored_offsets=[]),
		Key.D4: LayerKey(Key.D4, 13, ignored_offsets=[]),
		Key.D5: LayerKey(Key.D5, 14, ignored_offsets=[40, 60, 80, 100]),
		Key.D6: LayerKey(Key.D6, 15, ignored_offsets=[40, 60, 80, 100]),
		Key.D7: LayerKey(Key.D7, 16, ignored_offsets=[40, 60, 80, 100]),
		Key.D8: LayerKey(Key.D8, 17, ignored_offsets=[40, 60, 80, 100]),
		Key.D9: LayerKey(Key.D9, 18, ignored_offsets=[40, 60, 80, 100]),
		Key.D0: LayerKey(Key.D0, 19, ignored_offsets=[40, 60, 80, 100]),
	}

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

# Keyboard layers
if not k_toggle and not freelook:
	if keyboard.getKeyDown(Key.Z):
		active_layer_offset = 40
	elif keyboard.getKeyDown(Key.X):
		active_layer_offset = 60
	elif keyboard.getKeyDown(Key.C):
		active_layer_offset = 80
	elif keyboard.getKeyDown(Key.V):
		active_layer_offset = 100
	else:
		active_layer_offset = 0
else:
	active_layer_offset = 0

for layer_key in layer_keys.values():
	layer_key.update(active_layer_offset, freelook=(freelook or k_toggle))

if active_profile is not None:
	active_profile.update(freelook=freelook, alt_pressed=alt_pressed, shift_pressed=shift_pressed, control_layer=control_layer, control_mode=control_mode, active_layer_offset=active_layer_offset)

diagnostics.watch(k_toggle)
diagnostics.watch(freelook)
diagnostics.watch(control_layer)
diagnostics.watch(active_profile.__class__.__name__ if active_profile else None)
diagnostics.watch(active_layer_offset)
tick += 1
