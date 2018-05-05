#!/usr/bin/env python

import math
import rospy
import numpy as np

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Int32
from styx_msgs.msg import Lane, Waypoint

from scipy.spatial import KDTree

from common.waypoints import WayPoints
from common import utils

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.

As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.

Once you have created dbw_node, you will update this node to use the status of traffic lights too.

Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.

TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 50 # Number of waypoints we will publish. You can change this number
# MAX_DECEL = 5

class WaypointUpdater(object):
    def __init__(self):
        # TODO: Add other member variables you need below
        self.pose = None
        self.stopline_wp_idx = -1
        self.waypoints = WayPoints()

        rospy.init_node('waypoint_updater')

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)
        rospy.Subscriber('/traffic_waypoint', Int32, self.traffic_cb)

        # TODO: Add a subscriber for /obstacle_waypoint below

        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)
        self.loop()

    def loop(self):
        # set the loop rate to be 50
        rate = rospy.Rate(50)
        while not rospy.is_shutdown():
            if self.pose and self.waypoints.has_waypoints():
                x = utils.get_pose_x(self.pose)
                y = utils.get_pose_y(self.pose)
                closest_waypoint_idx = self.waypoints.get_closest_waypoint_idx(x, y)
                self.publish_waypoints(closest_waypoint_idx)
            rate.sleep()

    def publish_waypoints(self, closest_waypoint_idx):
        lane = self.generate_lane(closest_waypoint_idx)
        self.final_waypoints_pub.publish(lane)

    def generate_lane(self, closest_waypoint_idx):
        farthest_waypoint_idx = closest_waypoint_idx + LOOKAHEAD_WPS
        lane = self.waypoints.get_lane_with_waypoints(closest_waypoint_idx, farthest_waypoint_idx)
        if self.stopline_wp_idx == -1 or self.stopline_wp_idx >= farthest_waypoint_idx:
            return lane

        lane.waypoints = self.decelerate_waypoints(lane.waypoints, closest_waypoint_idx)
        return lane

    def decelerate_waypoints(self, waypoints, closest_waypoint_idx):
        decelerated_waypoints = []
        for i, wp in enumerate(waypoints):
            p = Waypoint()
            p.pose = wp.pose
            stop_waypoint_idx = max(self.stopline_wp_idx - closest_waypoint_idx - 1, 0)
            dist = self.distance(waypoints, i, stop_waypoint_idx)
            
            # vel = math.sqrt(2 * MAX_DECEL * dist)

            vel = 0.006 * (dist * dist) + 1.5

            if vel < 1.6:
                vel = 0.0

            p.twist.twist.linear.x = min(vel, wp.twist.twist.linear.x)
            decelerated_waypoints.append(p)

        return decelerated_waypoints

    def pose_cb(self, pose):
        self.pose = pose

    def waypoints_cb(self, waypoints):
        self.waypoints.set_waypoints(waypoints)

    def traffic_cb(self, traffic_waypoint):
        self.stopline_wp_idx = traffic_waypoint.data

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0.0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist


if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')