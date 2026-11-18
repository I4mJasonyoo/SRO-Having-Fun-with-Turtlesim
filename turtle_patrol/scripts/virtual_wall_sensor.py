#!/usr/bin/env python3

import math
import rospy

from turtlesim.msg import Pose
from turtle_patrol.msg import WallSensor


# ==========================================
# SENSOR CONFIGURATION
# ==========================================

ARENA_MIN = 0.5
ARENA_MAX = 10.5

SAFE_DISTANCE = 1.0

SENSOR_ANGLE = math.radians(45.0)


class VirtualWallSensor:

    def __init__(self):

        rospy.init_node('virtual_wall_sensor')

        self.turtle_name = rospy.get_param(
            '~turtle_name', 'turtle1'
        )

        # Robot state
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.pose_received = False

        # Publisher
        self.sensor_pub = rospy.Publisher(
            '/wall_sensor',
            WallSensor,
            queue_size=10
        )

        # Subscriber
        self.pose_sub = rospy.Subscriber(
            '/' + self.turtle_name + '/pose',
            Pose,
            self.pose_callback
        )

        rospy.loginfo("Virtual Wall Sensor Ready")

        self.rate = rospy.Rate(20)

        self.sensor_loop()

    # ======================================
    # POSE CALLBACK
    # ======================================

    def pose_callback(self, msg):

        self.x = msg.x
        self.y = msg.y
        self.theta = msg.theta

        self.pose_received = True

    # ======================================
    # CALCULATE WALL DISTANCE
    # ======================================

    def calculate_distance(self, angle):

        dx = math.cos(angle)
        dy = math.sin(angle)

        distances = []

        # Right wall
        if dx > 0:
            distances.append((ARENA_MAX - self.x) / dx)

        # Left wall
        elif dx < 0:
            distances.append((ARENA_MIN - self.x) / dx)

        # Top wall
        if dy > 0:
            distances.append((ARENA_MAX - self.y) / dy)

        # Bottom wall
        elif dy < 0:
            distances.append((ARENA_MIN - self.y) / dy)

        positive_distances = [
            d for d in distances if d >= 0
        ]

        if not positive_distances:
            return 0.0

        return min(positive_distances)

    # ======================================
    # SENSOR LOOP
    # ======================================

    def sensor_loop(self):

        while not rospy.is_shutdown():

            if self.pose_received:

                sensor = WallSensor()

                # Front sensor
                sensor.front_distance = self.calculate_distance(
                    self.theta
                )

                # Left sensor
                sensor.left_distance = self.calculate_distance(
                    self.theta + SENSOR_ANGLE
                )

                # Right sensor
                sensor.right_distance = self.calculate_distance(
                    self.theta - SENSOR_ANGLE
                )

                # Wall detection
                sensor.near_front_wall = (
                    sensor.front_distance < SAFE_DISTANCE
                )

                sensor.near_wall = (
                    sensor.front_distance < SAFE_DISTANCE
                    or sensor.left_distance < SAFE_DISTANCE
                    or sensor.right_distance < SAFE_DISTANCE
                )

                self.sensor_pub.publish(sensor)

            self.rate.sleep()


# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':

    try:

        sensor = VirtualWallSensor()

    except rospy.ROSInterruptException:
        pass
