
cmake_minimum_required(VERSION 3.0.2)
project(turtle_patrol)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  turtlesim
  message_generation
)

###################################
## Custom Message and Service
###################################

add_message_files(
  FILES
  MissionStatus.msg
  WallSensor.msg
  HunterScore.msg
)

add_service_files(
  FILES
  StartMission.srv
)

generate_messages(
  DEPENDENCIES
  std_msgs
)

###################################
## Catkin Package
###################################

catkin_package(
  CATKIN_DEPENDS
  rospy
  std_msgs
  geometry_msgs
  turtlesim
  message_runtime
)

###################################
## Include Directories
###################################

include_directories(
  ${catkin_INCLUDE_DIRS}
)
