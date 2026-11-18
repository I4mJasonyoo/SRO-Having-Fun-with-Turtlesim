#!/usr/bin/env python3

import math
import rospy

from geometry_msgs.msg import Twist, PointStamped
from std_msgs.msg import Bool
from turtlesim.msg import Pose

from turtle_patrol.msg import MissionStatus


# ==========================================
# CONTROLLER CONFIGURATION
# ==========================================

KP_LINEAR = 1.5
KP_ANGULAR = 6.0

MAX_LINEAR_SPEED = 2.0
MAX_ANGULAR_SPEED = 4.0

DISTANCE_TOLERANCE = 0.1
ANGLE_TOLERANCE = 0.05


class TurtleController:

    def __init__(self):

        rospy.init_node('turtle_controller')

        # Turtle namespace
        self.turtle_name = rospy.get_param('~turtle_name', 'turtle1')
        
        rospy.loginfo("Controlling turtle: %s", self.turtle_name)

        # ==================================
        # ROBOT STATE
        # ==================================

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.pose_received = False
        self.target_received = False
        self.target_reached = False

        self.mission_active = False

        # ==================================
        # TARGET STATE
        # ==================================

        self.target_x = 0.0
        self.target_y = 0.0
        self.waypoint_index = 0

        # ==================================
        # PUBLISHERS
        # ==================================

        self.velocity_pub = rospy.Publisher(
            '/' + self.turtle_name + '/cmd_vel',
            Twist,
            queue_size=10
        )

        self.status_pub = rospy.Publisher(
            '/' + self.turtle_name + '/mission/status',
            MissionStatus,
            queue_size=10
        )

        # ==================================
        # SUBSCRIBERS
        # ==================================

        self.pose_sub = rospy.Subscriber(
            '/' + self.turtle_name + '/pose',
            Pose,
            self.pose_callback
        )

        self.target_sub = rospy.Subscriber(
            '/' + self.turtle_name + '/mission/target',
            PointStamped,
            self.target_callback
        )

        self.active_sub = rospy.Subscriber(
            '/' + self.turtle_name + '/mission/active',
            Bool,
            self.active_callback
        )

        rospy.loginfo("Turtle Controller Ready")

        # ==================================
        # CONTROL LOOP
        # ==================================

        self.rate = rospy.Rate(20)

        self.control_loop()

    # ======================================
    # POSE CALLBACK
    # ======================================

    def pose_callback(self, msg):

        self.x = msg.x
        self.y = msg.y
        self.theta = msg.theta

        self.pose_received = True

    # ======================================
    # MISSION ACTIVE CALLBACK
    # ======================================

    def active_callback(self, msg):

        self.mission_active = msg.data

        if not self.mission_active:

            self.target_received = False
            self.target_reached = False

            rospy.loginfo("Mission deactivated")

        else:

            rospy.loginfo("Mission activated")

    # ======================================
    # TARGET CALLBACK
    # ======================================

    def target_callback(self, msg):

        self.target_x = msg.point.x
        self.target_y = msg.point.y

        self.waypoint_index = msg.header.seq

        self.target_received = True
        self.target_reached = False

        rospy.loginfo(
            "New target received: Waypoint %d (%.2f, %.2f)",
            self.waypoint_index,
            self.target_x,
            self.target_y
        )

    # ======================================
    # ANGLE NORMALIZATION
    # ======================================

    def normalize_angle(self, angle):

        return math.atan2(
            math.sin(angle),
            math.cos(angle)
        )

    # ======================================
    # P-CONTROLLER
    # ======================================

    def control_loop(self):

        while not rospy.is_shutdown():

            # Default velocity is zero
            velocity = Twist()

            if (
                self.mission_active
                and self.pose_received
                and self.target_received
            ):

                # Calculate position error
                dx = self.target_x - self.x
                dy = self.target_y - self.y

                # Euclidean distance
                distance = math.sqrt(
                    dx**2 + dy**2
                )

                # Desired heading angle
                desired_angle = math.atan2(
                    dy,
                    dx
                )

                # Angular error
                angle_error = self.normalize_angle(
                    desired_angle - self.theta
                )

                # ==================================
                # WAYPOINT REACHED CHECK
                # ==================================

                if distance < DISTANCE_TOLERANCE:

                    self.target_reached = True

                # ==================================
                # P-CONTROLLER
                # ==================================

                if not self.target_reached:

                    # Angular P-controller
                    velocity.angular.z = max(
                        -MAX_ANGULAR_SPEED,
                        min(
                            MAX_ANGULAR_SPEED,
                            KP_ANGULAR * angle_error
                        )
                    )

                    # Rotate before moving forward
                    if abs(angle_error) > ANGLE_TOLERANCE:

                        velocity.linear.x = 0.0

                    else:

                        # Linear P-controller
                        velocity.linear.x = min(
                            MAX_LINEAR_SPEED,
                            KP_LINEAR * distance
                        )

                # ==================================
                # PUBLISH MISSION STATUS
                # ==================================

                status = MissionStatus()

                status.waypoint_index = self.waypoint_index

                status.total_waypoints = rospy.get_param(
                    '/' + self.turtle_name + '/mission/total_waypoints',
                    0
                )

                status.target_x = self.target_x
                status.target_y = self.target_y

                status.distance = distance

                # Completion is managed by waypoint_manager
                status.mission_complete = False

                self.status_pub.publish(status)

            # ==================================
            # PUBLISH VELOCITY
            # ==================================

            self.velocity_pub.publish(velocity)

            self.rate.sleep()


# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':

    try:

        controller = TurtleController()

    except rospy.ROSInterruptException:
        pass
