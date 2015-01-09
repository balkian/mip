import argparse
import logging
import pexpect
import sys
import time


class GattTool:
    PROMPT = '.*\[LE\]>'

    def __init__(self, interface, address):
        cmd = 'gatttool -i %s -b %s -I' % (interface, address)
        self.child = pexpect.spawn(cmd)
        self.child.logfile = sys.stdout
        self.child.expect(self.PROMPT, timeout=1)

    def connect(self):
        self.child.sendline('connect')
        self.child.expect(self.PROMPT, timeout=1)

    def disconnect(self):
        self.child.sendline('disconnect')
        self.child.expect(self.PROMPT, timeout=1)

    def charWriteCmd(self, handle, byte_vals=[]):

        val = ''
        for byte_val in byte_vals:
            val += '%2.2x' % (byte_val)

        cmd = 'char-write-cmd 0x%4.4x ' % (handle) + val
        logging.debug('gatttool cmd: %s' % (cmd))
        self.child.sendline(cmd)

    def charReadReply(self, handle ,command, timeout=1):
        """
        parse reply of the form: 
        Notification handle = 0x000e value: 38 33 30 30 46 46 30 30 30 30 30 30
        The return string is a series of hex numbers representing ascii chars e.g.
        = 56 51 48 70 70 48 48 48 48 48 48
        = '8' '3' '0' '0' 'f' 'f' '0' '0' '0' '0' '0' '0'
        The actual numbers you want back are hex numbers based on tuples of the letters e.g.:
        = 0x83 0x00 0xff 0x00 0x00 0x00
        Which is a reply from an 0x83 (read chest led) command telling you it is green
        (0x00,0xff,0x00) 
        This routine cheks the reply is from the correct command, unless command
        is set to -1 in which case the first notification received is returned.
        """
        self.child.expect(self.PROMPT, timeout)
        done = 0
        notificationCount =  0
        while(done == 0):
            logging.debug('charReadReply: Awaiting Notification handle')
            self.child.expect('Notification handle = 0x000e value:', timeout)
            logging.debug('charReadReply: Got Notification handle')
            returnString = self.child.readline()
            logging.debug('charReadReply: return string was: %s' % (returnString))
            # create list of decimal integers
            intList = [int(s,16) for s in returnString.split() if s.isdigit()]
            # create 2 char strings of ASCII characters represented by dec numbers
            hexStringList = []
#           logging.debug('charReadReply: looping over : %d' % (len(returnIntList)/2))
            for i in range(len(intList)/2):
#                logging.debug('charReadReply: i is: %d' % (i))
                ili = i * 2
                s = [ ]
#                logging.debug('charReadReply: ili is: %d' % (ili))
#                logging.debug('charReadReply: char 0 is: %c' % (chr(intList[ili])))
                s.append(chr(intList[ili]))
#                logging.debug('charReadReply: char 1 is: %c' % (chr(intList[ili+1])))
                s.append(chr(intList[ili+1]))
                hexStringList.append("".join(s))
                #for s in hexStringList:
                #    logging.debug('charReadReply: Hex String was: %s' % (s))
            # Convert 2 char string representation of hex numbers to a list
            # of decimal integers 0..255
            returnIntList = [int(s,16) for s in hexStringList]
            #for i in returnIntList:
            #    logging.debug('charReadReply: Hex: %x' % (i))
            #    logging.debug('charReadReply: Decimal: %d' % (i))
            for i in range(len(returnIntList)):
                logging.debug('charReadReply: Byte %d Hex: %x' % (i,returnIntList[i]))
            done = (command == returnIntList[0]) or (command == -1)
            if (done == 0):
                logging.debug('charReadReply: Expecting command %x, received command %x' % (command,returnIntList[0]))
                notificationCount += 1
        return returnIntList

class Mip:
    def __init__(self, gt):
        self.gt = gt
        self.gt.connect()   
        time.sleep(2)
 
    def playSound(self, id):
        self.gt.charWriteCmd(0x13, [0x06, id, 0])
        
    def setMipPosition(self, position):
        self.gt.charWriteCmd(0x13, [0x08, position])

    def distanceDrive(self, distance, angle=0):
        """
            distance (+/-m)
            angle    (+/-deg)
        """

        if distance > 0:
            direction = 0
        else:
            direction = 1
        distance = abs(distance)

        if angle > 0:
            rotation = 0
        else:
            rotation = 1
        angle = abs(angle)
        self.gt.charWriteCmd(
            0x13, [
                0x70, 
                direction, 
                int(round(distance * 100)), 
                rotation, angle >> 8, 
                angle & 0xff])

        t = distance * 5
        time.sleep(t)

    def driveWithTime(self, speed, time_):
        """
            speed (-30...+30)
            time  (s)
        """

        t = int(round(time_/0.05))

        speed_mag = abs(speed)
        speed_sign = speed/speed_mag

        if speed_sign > 0:
            # Forward
            self.gt.charWriteCmd(0x13, [0x71, speed_mag, t/0.07])
        else:
            # Reverse
            self.gt.charWriteCmd(0x13, [0x72, speed_mag, t/0.07])

    def turnByAngle(self, angle, speed=15):
        """
            angle (deg)
            speed (0-24)
        """

        angle_mag = abs(angle)
        angle_sign = angle / angle_mag

        if angle_sign > 0:
            self.gt.charWriteCmd(
                0x13, [
                    0x74, 
                    int(round(angle_mag / 5.0)), 
                    speed])
        else:
            self.gt.charWriteCmd(
                0x13, [
                    0x73, 
                    int(round(angle_mag / 5.0)), 
                    speed])

        t = angle_mag / 360.0 * 0.9
        time.sleep(t)

    # Add continuous drive
    def stopDrive(self):
        """
        Stop continuous drive?
        """
        self.gt.charWriteCmd(0x13, [0x77])

    def continuousDriveForward(self, speed):
        """
        Start driving at a certain speed
        speed (0..32) (0x0..0x20)
        """
        if speed < 0:
            speed = 0
        if speed > 0x20:
            speed = 0x20
        self.gt.charWriteCmd(0x13, [0x78, speed])

    def continuousDriveBackward(self, speed):
        """
        Start driving at a certain speed
        speed (0..32) (0x0..0x20)
        """
        if speed < 0:
            speed = 0
        if speed > 0x20:
            speed = 0x20
        # backwards is actually 0x21-0x40, so add 0x20
        self.gt.charWriteCmd(0x13, [0x78, speed+0x20])


    def continuousTurnRight(self, speed):
        """
        Start turning right at a certain speed
        speed (0..32) (0x0..0x20)
        """
        if speed < 0:
            speed = 0
        if speed > 0x20:
            speed = 0x20
        # right is actually 0x40-0x60 
        self.gt.charWriteCmd(0x13, [0x78, speed+0x41])

    def continuousTurnLeft(self, speed):
        """
        Start turning left at a certain speed
        speed (0..32) (0x0..0x20)
        """
        if speed < 0:
            speed = 0
        if speed > 0x20:
            speed = 0x20
        # right is actually 0x61-0x80 
        self.gt.charWriteCmd(0x13, [0x78, speed+0x61])

    # Add set game mode

    def setChestLed(self, r, g, b):

        r = int(r * 255)
        g = int(g * 255)
        b = int(b * 255)

        self.gt.charWriteCmd(0x13, [0x84, r, g, b])

    def getChestLed(self):
        self.gt.charWriteCmd(0x13, [0x83])
        returnVals = self.gt.charReadReply(0x13, 0x83)
        colourVals = []
        # first return val is 0x83 - the request code
        colourVals.append(returnVals[1])
        colourVals.append(returnVals[2])
        colourVals.append(returnVals[3])
        return colourVals

    def getBatteryLevel(self):
        """
        Returns battery level in volts.
        Should be between 4.0v and 6.4v.
        """
        returnVals =  []
        returnVals = self.getMiPStatus()
        levelByte = returnVals[1]
        logging.debug('getBatteryLevel: level byte (0x4d = 4.0v,0x7c = 6.4v): %x' % (levelByte))
        # battery level 0x4d = 4.0v 0x7c = 6.4v
        # 2.4v in 0x2f
        voltage = ((levelByte-0x4d)*(2.4/0x2f)) + 4.0
        logging.debug('getBatteryLevel: voltage : %f' % (voltage))
        return voltage

    def getMiPOrientationStatus(self):
        """
        Return the current orientation of MiP
        0 - on back
        1 - face down
        2 - upright
        3 - picked up
        4 - hand stand
        5 - face down on tray
        6 - on back with kickstand
        """
        returnVals =  []
        returnVals = self.getMiPStatus()
        orientation = returnVals[2]
        logging.debug('getMiPOrientationStatus: status : %d' % (orientation))
        orientationString = ['on back' , 'face down' , 'upright' , 'picked up',
                             'hand stand' , 'face down on tray' , 
                             'on back with kickstand' ]
        logging.debug('getMiPOrientationStatus: %s' % (orientationString[orientation]))
        return orientation

    def getMiPStatus(self):
        retryCount = 0
        done = 0
        while((retryCount < 10) and (done == 0)):
            try:
                logging.debug('getMiPStatus: writing MiP Status request 0x79, attempt %d.' % (retryCount))
                self.gt.charWriteCmd(0x13, [0x79])
                returnVals = self.gt.charReadReply(0x13, 0x79)
                done = 1
            except pexpect.TIMEOUT:
                retryCount += 1
        return returnVals

    def getWeight(self):
        """
        Get how much weight MiP is holding.
        This is actually returmed as a float angle between -45 and 45
        As MiP is a balancing robot the angle is proportional to the weight 
        somehow.
        A negative angle means the weight is on the front
        A positive angle means the weight is on the back
        """
        logging.debug('getWeight: writing MiP Weight Update 0x81.')
        self.gt.charWriteCmd(0x13, [0x81])
        returnVals = self.gt.charReadReply(0x13, 0x81)
        weightByte = returnVals[1]
        logging.debug('getWeight: weight byte : %x' % (weightByte))
# 0xD3(-45 degree) - 0x2D(+45 degree)
# 0xD3 (211) (max)~0xFF(min) (255) is holding the weight on the front
# 0x00(min)~0x2D(max) is holding the weight on the back
        if weightByte < 0x2d:
            weightAngle = weightByte * 45.0 / 0x2d
        elif weightByte > 0xd3:
            weightAngle = ( weightByte - 0xff ) * 45.0 / ( 0xff - 0x2d )
        else:
            weightAngle = 0.0
            logging.debug('getWeight: weight angle (+ve = weight on back) : %f' % (weightAngle))
        return weightAngle

    def resetOdomemeter(self):
        logging.debug('resetOdomemeter: writing MiP Reset Odometer 0x86.')
        self.gt.charWriteCmd(0x13, [0x86])

    def getOdometer(self):
        """
        Return the odometer since the last reset in cm
        """
        distance = 0.0
        retryCount = 0
        done = 0
        while((retryCount < 10) and (done == 0)):
            try:
                logging.debug('getOdometer: writing MiP Get Odometer 0x85 : attempt %d.' % (retryCount))
                self.gt.charWriteCmd(0x13, [0x85])
                returnVals = self.gt.charReadReply(0x13, 0x85)
                # 4 byte return value, first byte is MSB
                odometerValue = (returnVals[1] << 24) + (returnVals[2] << 16) + (returnVals[3] << 8) + returnVals[4]
                logging.debug('getOdometer: Odometer value (48.5 per cm)  : %d' % (odometerValue))
                # 48.5 units per cm
                distance = odometerValue/48.5
                done = 1
            except pexpect.TIMEOUT:
                retryCount += 1
        return distance

    def setGestureRadarMode(self, mode):
        """
        Set whether to turn gesture or radar mode on.
        mode = 0 gesture off, radar off
        mode = 2 Gesture on, radar off
        mode = 4 Radar on, gesture off
        Note the radar updates only appear until the next command is sent?
        """
        logging.debug('setGestureRadarMode: writing MiP Set Gesture Radar Mode  0x0c %x .' % mode)
        self.gt.charWriteCmd(0x13, [0x0c, mode])

    def getRadarResponse(self):
        """
        Return current status of radar.
        Send a setGestureRadarMode(mode = 0x04) to trigger a reply
        return value 1 - no object
        return value 2 - object between 10cm-30cm
        return value 3 - object less than 10cm
        """
        retryCount = 0
        done = 0
        while((retryCount < 10) and (done == 0)):
            try:
                logging.debug('getRadarResponse: sending getRadarResponse  : attempt %d.' % (retryCount))
                # setGestureRadarMode(0x04) = turn Radar mode on
                self.gt.charWriteCmd(0x13, [0x0c, 0x04])
                returnVals = self.gt.charReadReply(0x13, 0x0c)
                thisResponse = returnVals[1]
                done = 1
            except pexpect.TIMEOUT:
                retryCount += 1
        logging.debug('getRadarResponse: response is %x.' % (thisResponse))
        # setGestureRadarMode(0x0) = turn Radar mode off
        self.gt.charWriteCmd(0x13, [0x0c, 0x0])
        return thisResponse

    def continousDriveForwardUntilRadar(self,speed):
        """
        Start driving at a certain speed
        speed (0..32) (0x0..0x20)
        Until a radar response is received that indicates we are near an object
        """
        # turn radar mode on
        logging.debug('continousDriveForwardUntilRadar: writing MiP Set Gesture Radar Mode  ON: 0x0c 0x04 .')
        self.gt.charWriteCmd(0x13, [0x0c, 0x04])
        radarResponse = 0
        orientation = 2
        done = 0
        while(done == 0):
            # continous drive forwards
            logging.debug('continousDriveForwardUntilRadar: Driving forwards at speed: %x .' % speed)
            self.gt.charWriteCmd(0x13, [0x78, speed])
            try:
                # Try and read a radar response, timeout after 0.02secs
                logging.debug('continousDriveForwardUntilRadar: Trying to read any response.')
                returnVals = self.gt.charReadReply(0x13, -1 ,timeout=0.02)
                if returnVals[0] == 0x0c:   # radar response
                    radarResponse = returnVals[1]
                    logging.debug('continousDriveForwardUntilRadar: Radar response was %d.' % radarResponse)
                elif returnVals[0] == 0x79: # MiPStatus response
                    # returnVals[1] is battery level
                    orientation = returnVals[2]
                    orientationString = ['on back' , 'face down' , 
                                         'upright' , 'picked up',
                                         'hand stand' , 'face down on tray' , 
                                         'on back with kickstand' ]
                    logging.debug('continousDriveForwardUntilRadar: MiP Status orientation %s' % (orientationString[orientation]))
            except pexpect.TIMEOUT:
                radarResponse = 0
                orientation = 2
                logging.debug('continousDriveForwardUntilRadar: NO Radar response.')
            # radarResponse value 0 - no radar response
            # radarResponse value 1 - no object
            # radarResponse value 2 - object between 10cm-30cm
            # radarResponse value 3 - object less than 10cm
            #  orientation 0 on back
            #  orientation 2 upright
            # Stop if we detect an object or we are not upright
            done = (radarResponse > 1) or (orientation != 2)
        # turn radar mode off
        logging.debug('continousDriveForwardUntilRadar: writing MiP Set Gesture Radar Mode  Off 0x0c 0x0 .')
        self.gt.charWriteCmd(0x13, [0x0c, 0x0])


    def setVolume(self, volume):
        """
        Set MiP sound volume:
        volume : 0..7
        """
        self.gt.charWriteCmd(0x13, [0x15, volume])

    def getVolume(self):
        """
        Return current MiP sound volume: 0..7
        """
        retryCount = 0
        done = 0
        while((retryCount < 10) and (done == 0)):
            try:
                logging.debug('getVolume: sending Command 0x16  : attempt %d.' % (retryCount))
                self.gt.charWriteCmd(0x13, [0x16])
                returnVals = self.gt.charReadReply(0x13, 0x16)
                volume = returnVals[1]
                done = 1
            except pexpect.TIMEOUT:
                retryCount += 1
        logging.debug('getVolume: volume is %x.' % (volume))
        return volume

class Turtle:
    def __init__(self, mip):
        self.mip = mip

    def left(self, angle):
        self.mip.turnByAngle(-angle)

    def right(self, angle):
        self.mip.turnByAngle(angle)

    def forward(self, distance):
        self.mip.distanceDrive(distance)

    def reverse(self, distance):
        self.mip.distanceDrive(-distance)


def add_arguments(parser):

    """Add gatttool-style arguments to an optparse parser."""

    parser.add_argument(
        '-i',
        '--adaptor',
        default='hci0',
        help='Specify local adaptor interface')

    parser.add_argument(
        '-b',
        '--device',
        default='D0:39:72:B8:C5:84',
        help='Specify remote bluetooth address')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Quick test program.')

    parser.add_argument(
        '-i', 
        '--adaptor', 
        default='hci0', 
        help='Specify local adaptor interface')

    parser.add_argument(
        '-b', 
        '--device',  
        default='D0:39:72:B8:C5:84', 
        help='Specify remote bluetooth address')

    args = parser.parse_args()

    gt = GattTool(args.adaptor, args.device)

    mip = Mip(gt)

    mip.playSound(0x4d)
