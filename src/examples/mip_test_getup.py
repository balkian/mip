#!/usr/bin/env python

"""
MiP Test program to try to get up
To Use:
./mip_test_clap.py -i hci0 -b D0:39:72:C4:7A:01

"""
import logging
import mippy
import argparse
import time

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Try to get up.')
    mippy.add_arguments(parser)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    gt = mippy.GattTool(args.adaptor, args.device)
    mip = mippy.Mip(gt)
    # enable clap recognition
    logging.debug('Enable clap')
    mip.setVolume(7)
    time.sleep(1)
    mip.getUp(0x0)
    while True:
        time.sleep(1)
        if abs(mip.getWeight()) < 15:
            break
        print("Not up yet")
    mip.playSound(16)
    mip.turnByAngle(850, speed=24)
