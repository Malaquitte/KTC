# Support for a manual controlled stepper supporting two endstops
#
# Copyright (C) 2026 Salagamor
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import stepper
import logging
from . import force_move

class DualEndstopStepper:
    def __init__(self, config):
        # Get Printer and Section name
        self.printer = config.get_printer()
        self.name = config.get_name()
        stepper_name = self.name.split()[1]

        # Retrieve both endstops pins, these are REQUIRED parameters
        endstop_pin_lock = config.get('endstop_pin_lock')
        endstop_pin_unlock = config.get('endstop_pin_unlock')

        # as the endstops are required, this stepper can home
        self.can_home = True

        # Create a config wrapper that renames endstop_pin_lock to endstop_pin for LookupRail
        class ConfigWrapper:
            def __init__(self, base_config, endstop_pin):
                self.base_config = base_config
                self.endstop_pin_value = endstop_pin
                logging.info("ConfigWrapper created with endstop_pin=%s" % endstop_pin)

            def get(self, option, default=None):
                logging.info("ConfigWrapper.get('%s', default=%s)" % (option, default))
                if option == 'endstop_pin':
                    logging.info("  -> returning endstop_pin_value=%s" % self.endstop_pin_value)
                    return self.endstop_pin_value
                result = self.base_config.get(option, default)
                logging.info("  -> returning %s" % result)
                return result
            
            def __getattr__(self, name):
                logging.info("ConfigWrapper.__getattr__('%s')" % name)
                return getattr(self.base_config, name)
                
        wrapped_config = ConfigWrapper(config, endstop_pin_lock)
        
        # Create main rail with the lock endstop
        self.rail = stepper.LookupRail(
                wrapped_config, need_position_minmax=False, default_position_endstop=0.)
        self.steppers = self.rail.get_steppers()

        # Create secondary MCU_Endstop for unlock
        self.mcu_endstop_unlock = self._create_mcu_endstop(config, endstop_pin_unlock)

        self.velocity = config.getfloat('velocity', 5., above=0.)
        self.accel = self.homing_accel = config.getfloat('accel', 50., minval=0.)
        self.next_cmd_time = 0.
        self.commanded_pos = 0.
        self.pos_min = config.getfloat('position_min', None)
        self.pos_max = config.getfloat('position_max', None)    
        # Setup iterative solver
        self.motion_queuing = self.printer.load_object(config, 'motion_queuing')
        self.trapq = self.motion_queuing.allocate_trapq()
        self.trapq_append = self.motion_queuing.lookup_trapq_append()
        self.rail.setup_itersolve('cartesian_stepper_alloc', b'x')
        self.rail.set_trapq(self.trapq)

        # Register commands
        gcode = self.printer.lookup_object('gcode')
        gcode.register_mux_command('DUAL_ENDSTOP_STEPPER', "STEPPER",
                                   stepper_name, self.cmd_DUAL_ENDSTOP_STEPPER,
                                   desc=self.cmd_DUAL_ENDSTOP_STEPPER_help)

    def _create_mcu_endstop(self, config, endstop_pin_str):
        """Create a MCU_Endstop with proper validation and registration."""
        ppins = self.printer.lookup_object('pins')
        # This call is here to validate the pin format
        pin_params = ppins.parse_pin(endstop_pin_str, True, True)
        
        # Create the MCU_Endstop via the pins system (with full validation)
        mcu_endstop = ppins.setup_pin('endstop', endstop_pin_str)
        mcu_endstop.add_stepper(self.rail.get_steppers()[0])
        
        # Register it in query_endstops
        query_endstops = self.printer.load_object(config, 'query_endstops')
        query_endstops.register_endstop(mcu_endstop, self.name)
    
        return mcu_endstop

    def get_name(self):
        return self.name
    
    # Required to synchronize the stepper moves with Toolhead moves
    def sync_print_time(self):
        toolhead = self.printer.lookup_object('toolhead')
        print_time = toolhead.get_last_move_time()
        if self.next_cmd_time > print_time:
            toolhead.dwell(self.next_cmd_time - print_time)
        else:
            self.next_cmd_time = print_time

    def do_enable(self, enable):
        stepper_names = [s.get_name() for s in self.steppers]
        stepper_enable = self.printer.lookup_object('stepper_enable')
        stepper_enable.set_motors_enable(stepper_names, enable)

    def do_set_position(self, setpos):
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.flush_step_generation()
        self.commanded_pos = setpos
        self.rail.set_position([self.commanded_pos, 0., 0.])

    def _submit_move(self, movetime, movepos, speed, accel):
        cp = self.commanded_pos
        dist = movepos - cp
        axis_r, accel_t, cruise_t, cruise_v = force_move.calc_move_time(
            dist, speed, accel)
        self.trapq_append(self.trapq, movetime,
                          accel_t, cruise_t, accel_t,
                          cp, 0., 0., axis_r, 0., 0.,
                          0., cruise_v, accel)
        self.commanded_pos = movepos
        return movetime + accel_t + cruise_t + accel_t
    
    def do_move(self, movepos, speed, accel, sync=True):
        self.sync_print_time()
        self.next_cmd_time = self._submit_move(self.next_cmd_time, movepos,
                                               speed, accel)
        self.motion_queuing.note_mcu_movequeue_activity(self.next_cmd_time)
        if sync:
            self.sync_print_time()

    def do_homing_move(self, movepos, speed, accel, triggered, check_trigger, use_unlock=False):   
        self.homing_accel = accel
        pos = [movepos, 0., 0., 0.]

        # Choose which endstop to use
        endstops = []
        if use_unlock:
            endstops.append((self.mcu_endstop_unlock, self.name))
            #endstops = [self.mcu_endstop_unlock]
        else:
            endstops = self.rail.get_endstops()
        
        phoming = self.printer.lookup_object('homing')
        phoming.manual_home(self, endstops, pos, speed,
                            triggered, check_trigger)

    cmd_DUAL_ENDSTOP_STEPPER_help = "Command a manually configured stepper with two endstops"
    def cmd_DUAL_ENDSTOP_STEPPER(self, gcmd):
        """
        Syntax: DUAL_ENDSTOP_STEPPER STEPPER=<name> [ENABLE=<0|1>] [SET_POSITION=<pos>] 
                [MOVE=<pos>] [SPEED=<speed>] [ACCEL=<accel>] [STOP_ON_ENDSTOP=<-2|-1|1|2>]
                [ENDSTOP=<LOCK|UNLOCK>] [SYNC=<0|1>]
        """
        enable = gcmd.get_int('ENABLE', None)
        if enable is not None:
            self.do_enable(enable)
        setpos = gcmd.get_float('SET_POSITION', None)
        if setpos is not None:
            self.do_set_position(setpos)
        speed = gcmd.get_float('SPEED', self.velocity, above=0.)
        accel = gcmd.get_float('ACCEL', self.accel, minval=0.)            
        homing_move = gcmd.get_int('STOP_ON_ENDSTOP', 0)
        if homing_move:
            movepos = gcmd.get_float('MOVE')
            if ((self.pos_min is not None and movepos < self.pos_min)
                or (self.pos_max is not None and movepos > self.pos_max)):
                raise gcmd.error("Move out of range")
            # Choose which endstop to use
            endstop_choice = gcmd.get('ENDSTOP', 'LOCK').upper()
            if endstop_choice not in ['LOCK', 'UNLOCK']:
                raise gcmd.error("ENDSTOP must be LOCK or UNLOCK")
        
            use_unlock = (endstop_choice == 'UNLOCK')
        
            self.do_homing_move(movepos, speed, accel,
                            homing_move > 0, abs(homing_move) == 1, 
                            use_unlock)
        elif gcmd.get_float('MOVE', None) is not None:
            movepos = gcmd.get_float('MOVE')
            if ((self.pos_min is not None and movepos < self.pos_min)
                or (self.pos_max is not None and movepos > self.pos_max)):
                raise gcmd.error("Move out of range")
            sync = gcmd.get_int('SYNC', 1)
            self.do_move(movepos, speed, accel, sync)
        elif gcmd.get_int('SYNC', 0):
            self.sync_print_time()

    def get_trapq(self):
        return self.trapq
    
    def flush_step_generation(self):
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.flush_step_generation()

    def get_position(self):
        return [self.commanded_pos, 0., 0., 0.]
    
    def set_position(self, newpos, homing_axes=""):
        self.do_set_position(newpos[0])

    def get_last_move_time(self):
        self.sync_print_time()
        return self.next_cmd_time
    
    def dwell(self, delay):
        self.next_cmd_time += max(0., delay)

    def drip_move(self, newpos, speed, drip_completion):
        # Submit move to trapq
        self.sync_print_time()
        start_time = self.next_cmd_time
        end_time = self._submit_move(start_time, newpos[0],
                                     speed, self.homing_accel)
        # Drip updates to motors
        self.motion_queuing.drip_update_time(start_time, end_time,
                                             drip_completion)
        # Clear trapq of any remaining parts of movement
        self.motion_queuing.wipe_trapq(self.trapq)
        self.rail.set_position([self.commanded_pos, 0., 0.])
        self.sync_print_time()

    def get_kinematics(self):
        return self
    
    def get_steppers(self):
        return self.steppers
    
    def calc_position(self, stepper_positions):
        return [stepper_positions[self.rail.get_name()], 0., 0.]


def load_config_prefix(config):
    return DualEndstopStepper(config)