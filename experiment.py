from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException

import tobii_research as tr
import numpy as np

###################################################
#################### Constants ####################
###################################################
# tracker sample frequency (Hz = sample/sec)
_SAMPLE_FREQ = 90
# Identifying fixations and saccades in eye-tracking protocols - Salvucci, Dario D. Goldberg, Joseph H.
# Sen and Megaw used a threshold of 20 degrees/second (= 0,349066 rad).
ANG_VELOCITY_THRESHOLD = 0.349066
# Minimum duration of a fixation before it is sent to the front-end (90 here is 1 second as per _SAMPLE_FREQ)
# Make sure this number is an integer at all times! Fixations are detected by an equality check where the number of
# samples is compared == INTEGER ! 15 samples ~= .1666666 second
FIXATION_TRIGGER = 1/6*_SAMPLE_FREQ

###################################################
##################### Globals #####################
###################################################
# previous sample (origin, u_target, s_target)
previous_sample = None
# Number of samples in the current fixation
fixation_duration = 0

###################################################
####################### IVT #######################
###################################################


def gaze_data_callback(gaze_data):
    """
    Process incoming gaze data sample.
    :param gaze_data: New data reading to be handled
    """
    ivt(gaze_data)


def ivt(gaze_data):
    """
    Determine fixation and actuate browser.
    :return:
    """
    global previous_sample, fixation_duration, body_size, driver

    # parse new sample
    origin, u_target, s_target = parse_data(gaze_data)

    if not previous_sample:
        previous_sample = origin, u_target, s_target
        pass

    p_origin, p_u_target, p_s_target = previous_sample

    # update previous sample
    previous_sample = origin, u_target, s_target

    # Calculate velocity (angle/sec) between previous sample and current sample
    ray1 = np.subtract(origin, u_target)
    ray2 = np.subtract(p_origin, p_u_target)
    angle = angle_between(ray1, ray2)

    # Label the new sample as either part of the fixation or a saccade, in which case the current fixation ends.
    if angle*_SAMPLE_FREQ > ANG_VELOCITY_THRESHOLD:
        if fixation_duration > 0:
            # print("Saccade. Fixation of {} seconds at {} ended.".format(fixation_duration/90, s_target))
            fixation_duration = 0
    else:
        fixation_duration += 1

    # Actuate if the current fixation exceeds the minimum trigger duration and lies in a contingent area
    if fixation_duration == FIXATION_TRIGGER:
        x, y = (body_size['width']*s_target[0], body_size['height']*s_target[1])
        if in_contingent_area(x, y):
            action_chains = ActionChains(driver)
            action_chains.move_by_offset(x, y).context_click().perform()
            action_chains.reset_actions()
            print("Clicked at {}{}".format(x, y))


def parse_data(gaze_data):
    """
    Parse raw gaze data into usable characteristics if all necessary data is valid.
    :param gaze_data: Gaze data to be parsed
    :return: origin, u_target, s_target || None in case of invalid input data
            <origin: user space eye coordinates>
            <u_target: user space gaze point coordinates>
            <s_target: display space gaze point coordinates>
    """
    if gaze_data["left_gaze_origin_validity"] and gaze_data["right_gaze_origin_validity"]:
        origin = average_vertex(
            gaze_data["left_gaze_origin_in_user_coordinate_system"],
            gaze_data["right_gaze_origin_in_user_coordinate_system"]
        )
        u_target = average_vertex(
            gaze_data["left_gaze_point_in_user_coordinate_system"],
            gaze_data["right_gaze_point_in_user_coordinate_system"],
        )
        # 2Dimensional inputs!
        s_target = average_vertex(
            gaze_data["left_gaze_point_on_display_area"],
            gaze_data["right_gaze_point_on_display_area"]
        )
        return origin, u_target, s_target
    return None


def average_vertex(v1, v2):
    """
    Calculate the center vertex. Default case 3D, other dimensions supported (slower implementation).
    :param v1: a vertex
    :param v2: another vertex
    :return: average of v1 and v2
    """
    if len(v1) != 3:
        return [sum(i) / len(i) for i in zip(*(v1, v2))]
    return ((v1[0]+v2[0])/2,
            (v1[1]+v2[1])/2,
            (v1[2]+v2[2])/2)


def unit_vector(vector):
    """ Returns the unit vector of the vector. """
    return vector / np.linalg.norm(vector)


def angle_between(v1, v2):
    """ Returns the angle in radians between vectors 'v1' and 'v2' """
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))


def in_contingent_area(x, y):
    global body_size, driver
    selection_x = body_size['width'] / 4
    search_x = body_size['width'] / 4 * 3
    selection_y = 70 + (body_size['height'] - 70) / 3
    center_y_up = body_size['height'] - 100
    search_y = 130
    recommend_y = 70

    # fixation in informationview
    if x > search_x:
        return False
    # fixation in selectionview
    if x < selection_x:
        # fixation in seedview
        if y > selection_y:
            return True
        # fixation outside seedview
        return False
    # fixation in centerview
    if y > recommend_y and y < center_y_up:
        try:
            # search view
            driver.find_element_by_tag_name('input')
            if y > search_y:
                return True
        except NoSuchElementException:
            # recommendationview
            return True


def start_tracker():
    tracker = tr.find_all_eyetrackers()[0]
    if tracker:
        print("Successfully connected to eyetracker '{tracker_name}'".format(tracker_name=tracker.device_name))
    tracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
    input("PRESS ANY KEY TO EXIT SCRIPT.")
    tracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)

###################################################
###################### Selen ######################
###################################################


driver = webdriver.Firefox()
driver.fullscreen_window()

# open the application
driver.get('http://localhost:3000/')

# wait for logged application (after oauth redirection)
wait = WebDriverWait(driver, 300)
wait.until(EC.url_contains("?access_token="))

# get body dimension for action offset
body = driver.find_element_by_tag_name('body')
body_size = body.size

start_tracker()
