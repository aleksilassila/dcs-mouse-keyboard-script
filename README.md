# DCS Mouse and Keyboard Guide

Contrary to popular belief, mouse and keyboard controls in DCS can be both enjoyable and competitive with HOTAS setups. This repository documents my freepie script for flying the f16 and other aircraft in DCS.

**Script features:**

- Custom mouse curves and trim behavior for pitch/roll
- Keybinds for all HOTAS buttons and switches using keyboard layers
- Clickable cockpit mode for easy interaction with cockpit and alt-tabbing
- Pedal control mode for easy taxi and takeoff
- Profiles for different aircraft

**Table of contents:**

- [1. FAQ](#faq)
- [2. Getting started](#getting-started)
- [3. Script features & documentation](#script-features--documentation)
  - [3.1 Script layer topology](#script-layer-topology)
  - [3.2 Aircraft mouse behavior and keybinds](#aircraft-mouse-behavior-and-keybinds)
  - [3.3 F-16 keybinds](#f-16-keybinds-wip)
  - [3.4 FA-18 keybinds](#fa-18-keybinds-more-wip)
- [4. Bonus: Designing joystick mouse controls](#bonus-designing-joystick-mouse-controls)
  - [4.1 The problem](#the-problem)
  - [4.2 Mapping mouse speed to joystick position](#mapping-mouse-speed-to-joystick-position)
  - [4.3 The two solutions](#the-two-solutions)
  - [4.4 Adjusting the curve variables](#adjusting-the-curve-variables)
  - [4.5 Pitch vs roll centering](#pitch-vs-roll-centering)
- [5. Bonus: Designing keyboard controls](#bonus-designing-keyboard-controls)
  - [5.1 What makes a good keyboard layout?](#what-makes-a-good-keyboard-layout)
- [6. Flying helicopters with mouse and keyboard](#flying-helicopters-with-mouse-and-keyboard)
- [7. Demo clips](#clips)
- [8. About this repo](#about-this-repo)

## FAQ

**How competitive is M&K with HOTAS?** In modern aircraft, you can do everything a HOTAS player can do + everything is programmable. You can find some clips of me flying with M&K in the [Clips](#clips) section below.

---

**What hardware do I need for flying?** Mouse and keyboard to get started. You also want to have head tracking, for this you need a webcam or a phone.

---

**What software do I need for flying?** [FreePIE](https://andersmalmgren.github.io/FreePIE/), vJoy and [Opentrack](https://github.com/opentrack/opentrack) for head tracking.

<details>

<summary>What do these programs do? (click to expand)</summary>

FreePIE is a program that allows you to use scripts to map your input devices to virtual joysticks and other output devices. In this case, we will use it to map our mouse and keyboard inputs to a virtual joystick that DCS can recognize.

vJoy is a virtual joystick driver that creates virtual joystick devices on your computer. In other words, it acts as if you had a physical joystick connected to your computer that will show up in DCS. You can control the virtual stick programmatically using FreePIE.

</details>

---

**Do I need to know how to program?** Not really, if you want to just use the script.

---

**What modules work the best with M&K?**

<details>

<summary>Fly-by-wire aircraft and helicopters (click to expand)</summary>

I've tried F-16, F/A-18, A-4E-C, UH-60L, OH-6A and UH-1H. Out of these, the only ones that I had trouble with were the OH-6A and UH-1H.

</details>

## Getting started

1. Download and install [FreePIE](https://andersmalmgren.github.io/FreePIE/), [vJoy](https://sourceforge.net/projects/vjoystick/) (and [Opentrack](https://github.com/opentrack/opentrack) for head tracking)

2. Download the [FreePIE script](DCS.v1.py) from this repository.

3. Use vJoy configurator to create two virtual joysticks. The first should have ~128 buttons. The second is needed for additional axes.

|       Joystick 1       |       Joystick 2       |
| :--------------------: | :--------------------: |
| ![](assets/vjoy-1.png) | ![](assets/vjoy-2.png) |

4. Open the downloaded script in FreePIE, press F5 to run the script.

5. When you start it, F16 profile is selected by default (I use it for both F-16 and FA-18). To change the profile, press `mouse 4` + `<number>`.
   - The "view" debug console in FreePIE shows you some useful variables such as module you have enabled and whether you are in cockpit mode

6. Exit cockpit mode by pressing `GRAVE` key (see [Script layer topology](#script-layer-topology)).

7. Update your DCS keybinds. The script utilises 4+1 keyboard layers that map to virtual joystick buttons, see below for detailed explanation. You need to unbind all the layered keys and then rebind them under the virtual joystick's buttons. For example, if you want to bind `X + W` to RCS up, in DCS unbind `W` and `X` from everything, then click add bind under the virtual joystick and press the key combination. You should see `JOY_BTN[NUMBER]` bound.
   - Keys `WASDQE` in the default layer are used for axis, you can't rebind them without modifying the script.
   - Mouse 1 & 2 emit `JOY_BTN[21]` and `JOY_BTN[22]`. Holding `mouse 4` prevents this, which is useful when assigning keybinds.

## Script features & documentation

This section explains in detail how to use the script.

### Script layer topology

The script has 3 layers of logic as pictured below: profiles, control modes, and `Z-V` keyboard layers.

```
.
├── UH-60L (`Profile 1`)
│   └── ...
├── UH-1H (`Profile 3`)
│   └── ...
├── F-16/FA-18 (`Profile 5`)
│   ├── Cockpit mode (Mouse 5)
│   └── Control mode (GRAVE key, next to 1 key)
│       ├── Pedal control mode (R, GRAVE to exit to default control mode)
        └── Z-V layers (hold layer key to enable)
```

1. **Profiles** are the top level layers. Each profile has different mouse curves and control behavior for different aircraft. You can switch between profiles on the fly by pressing `mouse 4` + `<number>`. When you start the script, F-16 is selected.

2. When you have a profile selected, you can toggle between **cockpit mode** and **control mode** using `mouse 5` and `GRAVE`.
   - In cockpit mode, your mouse is detached from the virtual joystick, cockpit clickable cursor is enabled and keyboard shortcuts are disabled. Enable cockpit mode if you want to interact with cockpit, look at f10 map or alt-tab out of the game.
   - In control mode, your mouse controls the virtual joystick and keyboard shortcuts are enabled. (From here you can enable pedal control mode.)
   - To make clickable cockpit mode also enable cursor in DCS, `JOY_BTN[30]` is emitted any time you change in or out of cockpit mode. You can bind it to the enable/disable cockpit interaction key in DCS.

3. Pedal control mode is a submode of control mode where your mouse controls your pedals instead of pitch and roll. Use this for taxi and takeoff. To enable it, press `R` while in control mode. To exit it, press `GRAVE` to go back to default control mode.

4. **`Z-V` keyboard layers** can be accessed while in control mode.

### Aircraft mouse behavior and keybinds

**Mouse curves and behavior**

- Pitch is always trimmed, in other words when you don't move your mouse, the virtual joystick's pitch will stay where you left it.
- When `mouse 5` is held, pitch is trimmed to center. Use this when you want to move your pitch perfectly center. Key is sticky for 1s after release.

- Roll is always trimmed to center.
- `shift + A/D` and `shift + F` can be used to trim the roll or reset the trim to center.
- Small constant rate and medium linear rate center the roll to trim location at all times.

- `mouse wheel` zooms in (smoothly, via `slider` axis). Holding `shift` while zooming controls virtual joystick 2's `slider` axis that can be bound to aircraft's manual zoom knob, for example.

https://github.com/user-attachments/assets/cd6dbf61-f284-4e64-baed-f5deeb9e877a

**Mouse keybinds**

- `mouse 1`: gun
- `mouse 2` (F-16): enable btn (held)
- `mouse wheel`: press toggles between 2 zoom level presets
- `mouse 4`: enter freelook mode (disable all keybinds, detach mouse from joystick, enable clickable cockpit)
- `mouse 5`: hold to trim pitch to center, or trim pedals to center if in pedal control mode

### F-16 keybinds

**Keyboard keybinds**

![F-16 keybinds](assets/f16.png)

The rest of the keyboard uses the default DCS keybinds.

### FA-18 keybinds (wip)

![FA-18 keybinds](assets/fa18.png)

## Bonus: Designing joystick mouse controls

This section covers the theory behind efficient joystick emulation using a mouse. It should also help you adjust the mouse curves for the best experience.

### The problem

In order to understand what are the optimal mouse curves and control behavior, one needs to understand the differences between mouse and joystick as input devices. What the joystick does that the mouse doesn't:

- Joystick gives you physical feedback on where you are with respect to the center and max limits, because it has a fixed range of motion.

On the other hand, mouse gives you:

- Configurable sensitivity and higher precision, especially compared to budget joysticks.

The problem with the mouse is that you easily lose mental track of where your virtual joystick is. If you can somehow get feedback of where your mouse is with respect to the virtual joystick center and max limits, controlling the virtual joystick becomes easy. In other words, your eye-hand-coordination needs a feedback loop.

### Mapping mouse speed to joystick position

One solution to the lack of physical feedback is to map mouse speed to joystick position directly. You can do this with the following formula:

`joystick_position = min(mouse_delta / sensitivity, max_limit)`

...where the mouse delta is the distance you've moved since the last tick (update). You'd also apply moving average smoothing to the mouse delta.

This makes it so that if moving your mouse at X pixels per second corresponds to max joystick deflection, moving the mouse at X/2 pixels per second corresponds to half deflection and letting go of the mouse would center the stick almost immediately.

The problem with this approach is that controlling hand speed is much harder than controlling hand position or distance moved. I tried this approach and while it did fix the lack of feedback, it was way too inaccurate to be able to hold a specific joystick position even after applying smoothing to the speed input. I was either running out of mousepad or not having enough accuracy.

### The two solutions

The solution(s) to our problem exploit the fact that you only need precise control over the joystick near the center. This means that the closer to the max limit you are, the more you can control the stick using the speed of your mouse movement without suffering from the inaccuracy of speed control. Near the center you need to be able to have very precise control, meaning that the input method should be relative and not based on speed. This would naturally give us the following curve:

![Curve 1](assets/curve-1.png)

Now it's easy to get feedback when you are near the max limit, but another problem remains. When trying to center the stick from a high deflection, the stick won't center perfectly because the centering force gets exponentially weaker the closer you are to the center. For this reason, we need to add a small constant centering force that is applied at all times, so that the virtual stick will always perfectly center itself even if you don't quite hit the center. Together these curves look like this:

![Curve 1](assets/curve-2.png)

We want to keep the curve as simple as possible (hence the linear shape) because accurate mouse joystick emulation relies on muscle memory and intuition of the virtual joystick position. Even if a more complex curve would give you better theoretical accuracy, it's not worth it for the much increased learning time.

### Adjusting the curve variables

The above curves use example values. To find the optimal curve variables you can use the following logic:

- The bigger the linear component, the less your mouse acts like relative input and the more feedback you get about how far you are from the joystick max limit. If you increase it too much, you lose precision and can run out of mouse pad when trying to hold a large deflection. Try to have set it as large as possible while being able to do 95% of the mouse movements with only your wrist. Lifting your arm always results in less precise movements.

- The bigger the constant centering force, the easier and quicker it will be to center the stick. However, you need to always overcome the constant component when moving the mouse, meaning that it sets a sort of minimum mouse speed that you need to meet to be able to move the stick at all. That's not great for precision, so I'd set it as low as possible without suffering from over or undershooting the center when returning from stick deflection. The magnitude of the constant component is a compromise between ease of centering and precision near the center.

### Pitch vs roll centering

I've found that it's best to use hold-to-enable centering for pitch, and always center roll. This is because you want to be able to hold a specific pitch angle in a turn, where as roll rarely requires sustained hold at high deflection. Rather you'd initiate the turn with a roll and then apply a slight roll together with pitch to sustain it. After a turn you'd hold the pitch centering button while leveling the aircraft to perfectly hit the center of the stick.

If you need to maneuver without looking forward, you can do it accurately by holding the pitch centering button so that it acts the same way as roll. Without visual feedback you are limited when it comes to holding a high pitch deflection accurately. This almost never matters though and you can practice it.

## Bonus: Designing keyboard controls

I use 4+1 keyboard layers for my keybinds in addition to `shift` and `ctrl` used as modifiers occasionally. This means the keys `1-4`, `Q-R` and `A-F` behave differently depending on which of the keys `Z-V` is held down (I have dubbed the 5th layer (when nothing is held) as the _control layer_). In total this gives me 5 x 3 x 4 = 60 buttons that I can press without moving my left hand from the WASD position in addition to a couple of other non-layered keys.

DCS itself has partial support for layers, but it lacked some logic that I wanted to program in (such as hold to enable layer iirc), so the layered keys map to the virtual joystick's `buttons 0-115`. To map keys, you need to a) unbind keys `1-V` from everything and b) when binding layered keys, bind them under the virtual joystick's buttons by pressing the desired key. Furthermore, the control layer contains axis bindings such as throttle and pedals that you can't rebind without modifying the script, but the rest of the layered keys are free to bind as you wish.

### What makes a good keyboard layout?

I designed my layout with the following in mind:

- Must be able to press all aircraft HOTAS keys without moving left hand from WASD position
- Must have enough keys to bind all HOTAS buttons (layers!)
- Keys that need to be pressed at the same time can't be in different layers
- Must be intuitive to use and remember

In addition, I try to avoid toggles because they require you to keep track of the state of the toggle. Instead I prefer having two different keys for on and off, or hold to enable behavior. This is why cockpit mode has two separate keys for on and off instead of a toggle key.

## Flying helicopters with mouse and keyboard

- Bind pedals to mouse wheel. It will be unintuitive at first, but necessary for advanced maneuvers and handy when you get used to it.
- Having a button in your mouse that doubles your dpi when held helps. This way you can have lower sensitivity for precision when hovering and higher sensitivity for forward flight.
- Helicopters that don't have fly-by-wire, where you need to always hold some amount of roll, will require you to enable continuous trim for both pitch and roll as opposed to just pitch.

## Clips

Some clips that demonstrate the accuracy that can be achieved with mouse and keyboard controls:

Combat & maneuvering

https://github.com/user-attachments/assets/d8cfc1b6-5361-40e1-9aa1-a54ff2a8993d

https://github.com/user-attachments/assets/50ba377a-6bc7-4888-86d2-e259131cbe4d

F/A-18 cockpit management

https://github.com/user-attachments/assets/e2ec50a4-362f-47fc-ad5b-f82c37b62a90

UH-60L:

https://github.com/user-attachments/assets/9725a4e2-3b2b-471a-a2ff-d3ec70427224

https://github.com/user-attachments/assets/2a6d1d8a-7f4f-4601-a249-5581a641ccf1

## TODO

- Finalize helicopter profiles

## About this repo

Keybind diagrams were created using [keyboard shortcut map maker](https://archie-adams.github.io/keyboard-shortcut-map-maker/).

AI prompting was not used to write this guide. Next word prediction was occasionally used for individual words. Early versions of the script had vibe coded parts.
