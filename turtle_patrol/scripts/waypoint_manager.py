#!/usr/bin/env python3

import rospy

from geometry_msgs.msg import PointStamped
from std_msgs.msg import Bool
from turtlesim.srv import SetPen

from turtle_patrol.msg import MissionStatus
from turtle_patrol.srv import StartMission, StartMissionResponse


# ==========================================
# WAYPOINT CONFIGURATION
# ==========================================

WAYPOINTS = [
    (5.5, 9.5),
    (5.9, 6.4),
    (7.2, 7.2),
    (6.4, 5.9),
    (9.5, 5.5),
    (6.4, 5.1),
    (7.2, 3.8),
    (5.9, 4.6),
    (5.5, 1.5),
    (5.1, 4.6),
    (3.8, 3.8),
    (4.6, 5.1),
    (1.5, 5.5),
    (4.6, 5.9),
    (3.8, 7.2),
    (5.1, 6.4),
    (5.5, 9.5)
]

DISTANCE_TOLERANCE = 0.1


class WaypointManager:

    def __init__(self):

        rospy.init_node('waypoint_manager')

        # ==================================
        # TURTLE CONFIGURATION
        # ==================================

        self.turtle_name = rospy.get_param(
            '~turtle_name', 'turtle1'
        )

        rospy.loginfo(
            "Managing patrol for: %s",
            self.turtle_name
        )

        # ==================================
        # MISSION VARIABLES
        # ==================================

        self.current_index = 1
        self.mission_active = False
        self.mission_complete = False

        rospy.set_param(
            '/' + self.turtle_name + '/mission/total_waypoints',
            len(WAYPOINTS)
        )

        # ==================================
        # PUBLISHERS
        # ==================================

        self.target_pub = rospy.Publisher(
            '/' + self.turtle_name + '/mission/target',
            PointStamped,
            queue_size=10,
            latch=True
        )

        self.active_pub = rospy.Publisher(
            '/' + self.turtle_name + '/mission/active',
            Bool,
            queue_size=10,
            latch=True
        )

        # Initial mission state
        self.active_pub.publish(Bool(data=False))

        # ==================================
        # SUBSCRIBERS
        # ==================================

        self.status_sub = rospy.Subscriber(
            '/' + self.turtle_name + '/mission/status',
            MissionStatus,
            self.status_callback
        )

        # ==================================
        # PEN SERVICE
        # ==================================

        pen_service_name = (
            '/' + self.turtle_name + '/set_pen'
        )

        # Create proxy without waiting.
        # This prevents startup deadlock in Dogfight mode.

        self.set_pen = rospy.ServiceProxy(
            pen_service_name,
            SetPen
        )

        rospy.loginfo("Pen service proxy created")

        # ==================================
        # START MISSION SERVICE
        # ==================================

        if self.turtle_name == 'turtle1':

            service_name = '/start_mission'

        else:

            service_name = (
                '/' + self.turtle_name + '/start_mission'
            )

        self.start_service = rospy.Service(
            service_name,
            StartMission,
            self.start_callback
        )

        rospy.loginfo(
            "Start mission service ready: %s",
            service_name
        )

        rospy.loginfo("Waypoint Manager Ready")

        rospy.loginfo(
            "Total waypoints: %d",
            len(WAYPOINTS)
        )

    # ======================================
    # PEN CONTROL
    # ======================================

    def control_pen(self):

        try:

            # Disable pen before waypoint 1
            # and during transition waypoint 4 -> 5

            if self.current_index in [1]:

                self.set_pen(0, 0, 0, 1, 1)

                rospy.loginfo("Pen disabled")

            else:

                self.set_pen(0, 0, 255, 3, 0)

                rospy.loginfo("Blue pen enabled")

        except rospy.ServiceException as e:

            rospy.logwarn(
                "Unable to control pen: %s", e
            )

    # ======================================
    # START MISSION CALLBACK
    # ======================================

    def start_callback(self, request):

        if not request.start:

            return StartMissionResponse(
                False,
                "Start request rejected"
            )

        if self.mission_active:

            return StartMissionResponse(
                False,
                "Mission is already running"
            )

        # Reset mission
        self.current_index = 1
        self.mission_active = True
        self.mission_complete = False

        rospy.loginfo("================================")
        rospy.loginfo("MISSION STARTED!")
        rospy.loginfo("================================")

        # Activate controller
        self.active_pub.publish(Bool(data=True))

        # Send first waypoint
        self.publish_target()

        return StartMissionResponse(
            True,
            "Mission started successfully"
        )

    # ======================================
    # PUBLISH TARGET
    # ======================================

    def publish_target(self):

        if self.current_index > len(WAYPOINTS):

            self.finish_mission()
            return

        # Configure pen before moving
        self.control_pen()

        target = PointStamped()

        target.header.stamp = rospy.Time.now()
        target.header.seq = self.current_index

        target.point.x = WAYPOINTS[
            self.current_index - 1
        ][0]

        target.point.y = WAYPOINTS[
            self.current_index - 1
        ][1]

        target.point.z = 0.0

        self.target_pub.publish(target)

        rospy.loginfo(
            "Target %d: (%.2f, %.2f)",
            self.current_index,
            target.point.x,
            target.point.y
        )

    # ======================================
    # MISSION COMPLETION
    # ======================================

    def finish_mission(self):

        self.mission_active = False
        self.mission_complete = True

        # Deactivate controller
        self.active_pub.publish(Bool(data=False))

        # Disable pen
        try:

            self.set_pen(0, 0, 0, 1, 1)

        except rospy.ServiceException as e:

            rospy.logwarn(
                "Unable to disable pen: %s", e
            )

        rospy.loginfo("================================")
        rospy.loginfo("MISSION COMPLETED!")
        rospy.loginfo("All waypoints have been reached.")
        rospy.loginfo("================================")

    # ======================================
    # STATUS CALLBACK
    # ======================================

    def status_callback(self, msg):

        if not self.mission_active:
            return

        # Check waypoint index
        if msg.waypoint_index != self.current_index:
            return

        # Check waypoint distance
        if msg.distance < DISTANCE_TOLERANCE:

            rospy.loginfo(
                "Waypoint %d reached! Distance: %.3f",
                self.current_index,
                msg.distance
            )

            self.current_index += 1

            if self.current_index > len(WAYPOINTS):

                self.finish_mission()

            else:

                self.publish_target()


# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':

    try:

        manager = WaypointManager()
        rospy.spin()

    except rospy.ROSInterruptException:

        pass
