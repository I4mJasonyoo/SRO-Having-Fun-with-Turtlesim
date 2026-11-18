#!/usr/bin/env python3

import math
import random
import rospy

from geometry_msgs.msg import Twist
from turtlesim.msg import Pose
from turtlesim.srv import Spawn, Kill

from turtle_patrol.msg import HunterScore
from turtle_patrol.srv import StartMission


# ==========================================
# HUNTER CONFIGURATION
# ==========================================

KP_LINEAR = 2.5
KP_ANGULAR = 6.0

MAX_LINEAR_SPEED = 3.0
MAX_ANGULAR_SPEED = 4.0

ANGLE_TOLERANCE = 0.05
CAPTURE_DISTANCE = 0.5

SPAWN_MIN = 1.0
SPAWN_MAX = 10.0
MIN_SPAWN_DISTANCE = 2.5


class HunterController:

    def __init__(self):

        rospy.init_node('hunter_controller')

        # ==================================
        # TARGET BEHAVIOR MODE
        # ==================================

        self.target_mode = rospy.get_param(
            '~target_mode', 'patrol'
        )

        rospy.loginfo(
            "Target mode: %s",
            self.target_mode
        )

        # Validate target mode
        if self.target_mode not in [
            'patrol',
            'stationary',
            'explorer'
        ]:

            rospy.logerr(
                "Invalid target mode: %s",
                self.target_mode
            )

            return

        # ==================================
        # ROBOT STATE
        # ==================================

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.pose_received = False

        # Target state
        self.target_x = 0.0
        self.target_y = 0.0

        self.target_received = False
        self.target_name = ""

        self.target_sub = None

        # Score
        self.score = 0
        self.targets_caught = 0

        # ==================================
        # PUBLISHER
        # ==================================

        self.velocity_pub = rospy.Publisher(
            '/turtle_h/cmd_vel',
            Twist,
            queue_size=10
        )

        self.score_pub = rospy.Publisher(
            '/hunter/score',
            HunterScore,
            queue_size=10,
            latch=True
        )

        # ==================================
        # SUBSCRIBERS
        # ==================================

        self.pose_sub = rospy.Subscriber(
            '/turtle_h/pose',
            Pose,
            self.pose_callback
        )

        # ==================================
        # SERVICES
        # ==================================

        rospy.loginfo(
            "Waiting for Turtlesim services..."
        )

        rospy.wait_for_service('/spawn')
        rospy.wait_for_service('/kill')

        self.spawn_service = rospy.ServiceProxy(
            '/spawn',
            Spawn
        )

        self.kill_service = rospy.ServiceProxy(
            '/kill',
            Kill
        )

        # ==================================
        # TARGET BEHAVIOR SERVICE
        # ==================================

        self.start_patrol_service = None

        if self.target_mode == 'patrol':

            rospy.loginfo(
                "Waiting for target Patrol service..."
            )

            rospy.wait_for_service(
                '/target/start_mission'
            )

            self.start_patrol_service = rospy.ServiceProxy(
                '/target/start_mission',
                StartMission
            )

            rospy.loginfo(
                "Target Patrol service connected"
            )

        elif self.target_mode in [
            'stationary',
            'explorer'
        ]:

            rospy.loginfo(
                "No Patrol service required for mode: %s",
                self.target_mode
            )

        # ==================================
        # SPAWN HUNTER
        # ==================================

        try:

            self.kill_service('turtle1')

            rospy.loginfo(
                "Default turtle1 removed"
            )

            self.spawn_service(
                5.544,
                5.544,
                0.0,
                'turtle_h'
            )

            rospy.loginfo(
                "Hunter spawned as turtle_h"
            )

        except rospy.ServiceException as error:

            rospy.logerr(
                "Failed to initialize hunter: %s",
                error
            )

            return

        rospy.loginfo(
            "Turtlesim services connected"
        )

        rospy.loginfo(
            "Hunter Controller Ready"
        )

        # ==================================
        # CONTROL LOOP
        # ==================================

        self.rate = rospy.Rate(20)

        self.publish_score("", 0.0)

        self.hunter_loop()

    # ======================================
    # HUNTER POSE CALLBACK
    # ======================================

    def pose_callback(self, msg):

        self.x = msg.x
        self.y = msg.y
        self.theta = msg.theta

        self.pose_received = True

    # ======================================
    # TARGET POSE CALLBACK
    # ======================================

    def target_callback(self, msg):

        self.target_x = msg.x
        self.target_y = msg.y

        self.target_received = True

    # ======================================
    # ANGLE NORMALIZATION
    # ======================================

    def normalize_angle(self, angle):

        return math.atan2(
            math.sin(angle),
            math.cos(angle)
        )

    # ======================================
    # SPAWN RANDOM TARGET
    # ======================================

    def spawn_target(self):

        self.target_received = False

        # Find a position sufficiently far
        # from the hunter

        for attempt in range(100):

            target_x = random.uniform(
                SPAWN_MIN,
                SPAWN_MAX
            )

            target_y = random.uniform(
                SPAWN_MIN,
                SPAWN_MAX
            )

            distance = math.sqrt(
                (target_x - self.x)**2
                + (target_y - self.y)**2
            )

            if distance >= MIN_SPAWN_DISTANCE:
                break

        else:

            rospy.logerr(
                "Unable to find spawn position"
            )

            return False

        try:

            response = self.spawn_service(
                target_x,
                target_y,
                random.uniform(-math.pi, math.pi),
                'target'
            )

            self.target_name = response.name

            # Subscribe to the new target pose

            self.target_sub = rospy.Subscriber(
                '/' + self.target_name + '/pose',
                Pose,
                self.target_callback
            )

            # ==================================
            # START TARGET BEHAVIOR
            # ==================================

            if self.target_mode == 'patrol':

                try:

                    response = self.start_patrol_service(
                        True
                    )

                    if response.success:

                        rospy.loginfo(
                            "Target Patrol started!"
                        )

                    else:

                        rospy.logwarn(
                            "Target Patrol failed: %s",
                            response.message
                        )

                        return False

                except rospy.ServiceException as error:

                    rospy.logerr(
                        "Failed to start target Patrol: %s",
                        error
                    )

                    return False

            elif self.target_mode == 'stationary':

                rospy.loginfo(
                    "Target is stationary"
                )

            elif self.target_mode == 'explorer':

                rospy.loginfo(
                    "Target Explorer activated"
                )

            rospy.loginfo(
                "Target spawned: %s at (%.2f, %.2f)",
                self.target_name,
                target_x,
                target_y
            )

            return True

        except rospy.ServiceException as error:

            rospy.logerr(
                "Spawn service failed: %s",
                error
            )

            return False

    # ======================================
    # PUBLISH SCORE
    # ======================================

    def publish_score(self, target_name, distance):

        msg = HunterScore()

        msg.score = self.score
        msg.targets_caught = self.targets_caught
        msg.target_name = target_name
        msg.capture_distance = distance

        self.score_pub.publish(msg)

    # ======================================
    # CAPTURE TARGET
    # ======================================

    def capture_target(self, distance):

        # Stop hunter
        self.velocity_pub.publish(Twist())

        captured_name = self.target_name

        try:

            # Remove target turtle
            self.kill_service(captured_name)

            self.score += 1
            self.targets_caught += 1

            rospy.loginfo(
                "=============================="
            )

            rospy.loginfo("TARGET CAPTURED!")
            rospy.loginfo("Target: %s", captured_name)
            rospy.loginfo("Distance: %.3f", distance)
            rospy.loginfo("Score: %d", self.score)

            rospy.loginfo(
                "=============================="
            )

            # Publish updated score

            self.publish_score(
                captured_name,
                distance
            )

            # Remove old subscriber

            if self.target_sub is not None:

                self.target_sub.unregister()
                self.target_sub = None

            self.target_name = ""
            self.target_received = False

        except rospy.ServiceException as error:

            rospy.logerr(
                "Kill service failed: %s",
                error
            )

    # ======================================
    # HUNTER CONTROL LOOP
    # ======================================

    def hunter_loop(self):

        while not rospy.is_shutdown():

            velocity = Twist()

            if not self.pose_received:

                self.rate.sleep()
                continue

            # Spawn target if none exists

            if not self.target_name:

                self.spawn_target()

                self.rate.sleep()
                continue

            if self.target_received:

                dx = self.target_x - self.x
                dy = self.target_y - self.y

                # Calculate distance

                distance = math.sqrt(
                    dx**2 + dy**2
                )

                # Calculate desired heading

                desired_angle = math.atan2(
                    dy,
                    dx
                )

                angle_error = self.normalize_angle(
                    desired_angle - self.theta
                )

                # Check capture distance

                if distance < CAPTURE_DISTANCE:

                    self.capture_target(distance)

                else:

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

            # Publish velocity

            self.velocity_pub.publish(velocity)

            self.rate.sleep()


# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':

    try:

        hunter = HunterController()

    except rospy.ROSInterruptException:

        pass