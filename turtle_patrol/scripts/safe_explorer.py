#!/usr/bin/env python3

import rospy

from geometry_msgs.msg import Twist
from turtle_patrol.msg import WallSensor


# ==========================================
# EXPLORER CONFIGURATION
# ==========================================

FORWARD_SPEED = 1.5
TURN_SPEED = 2.5

SAFE_DISTANCE = 1.0

TURN_DURATION = 1.0


class SafeExplorer:

    def __init__(self):

        rospy.init_node('safe_explorer')
        self.turtle_name = rospy.get_param(
            '~turtle_name', 'turtle1'
        )

        # Sensor state
        self.front_distance = 0.0
        self.left_distance = 0.0
        self.right_distance = 0.0

        self.near_front_wall = False
        self.near_wall = False

        self.sensor_received = False

        # Turning state
        self.turning = False
        self.turn_direction = 1

        self.turn_start_time = None

        # Publisher
        self.velocity_pub = rospy.Publisher(
            '/' + self.turtle_name + '/cmd_vel',
            Twist,
            queue_size=10
        )

        # Subscriber
        self.sensor_sub = rospy.Subscriber(
            '/wall_sensor',
            WallSensor,
            self.sensor_callback
        )

        rospy.loginfo("Safe Explorer Ready")

        self.rate = rospy.Rate(20)

        self.explorer_loop()

    # ======================================
    # SENSOR CALLBACK
    # ======================================

    def sensor_callback(self, msg):

        self.front_distance = msg.front_distance
        self.left_distance = msg.left_distance
        self.right_distance = msg.right_distance

        self.near_front_wall = msg.near_front_wall
        self.near_wall = msg.near_wall

        self.sensor_received = True

    # ======================================
    # EXPLORATION CONTROL
    # ======================================

    def explorer_loop(self):

        while not rospy.is_shutdown():

            velocity = Twist()

            if self.sensor_received:

                current_time = rospy.Time.now()

                # Check if turning is required
                if not self.turning:

                    if self.front_distance < SAFE_DISTANCE:

                        self.turning = True
                        self.turn_start_time = current_time

                        # Choose direction with more space
                        if self.left_distance > self.right_distance:

                            self.turn_direction = 1

                        else:

                            self.turn_direction = -1

                        rospy.loginfo(
                            "Wall detected! Turning..."
                        )

                # Execute turn
                if self.turning:

                    elapsed = (
                        current_time - self.turn_start_time
                    ).to_sec()

                    if elapsed < TURN_DURATION:

                        velocity.angular.z = (
                            self.turn_direction * TURN_SPEED
                        )

                    else:

                        self.turning = False

                        rospy.loginfo(
                            "Obstacle avoided. Moving forward."
                        )

                # Move forward when not turning
                else:

                    velocity.linear.x = FORWARD_SPEED

            # Publish velocity
            self.velocity_pub.publish(velocity)

            self.rate.sleep()


# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':

    try:

        explorer = SafeExplorer()

    except rospy.ROSInterruptException:
        pass
