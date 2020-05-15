import tobii_research as tr
import numpy as np

tracker = tr.find_all_eyetrackers()[0]
if tracker:
    print("Successfully connected to eyetracker '{tracker_name}'".format(tracker_name=tracker.device_name))

"""tracker sample frequency (Hz = sample/sec)"""
_SAMPLE_FREQ = 90


# Identifying fixations and saccades in eye-tracking protocols - Salvucci, Dario D. Goldberg, Joseph H.
# Sen and Megaw used a threshold of 20 degrees/second (= 0,349066 rad).
ANG_VELOCITY_THRESHOLD = 0.349066

# Minimum duration of a fixation before it is sent to the front-end (90 here is 1 second as per _SAMPLE_FREQ)
FIXATION_TRIGGER = .3*_SAMPLE_FREQ


# previous sample (origin, u_target, s_target)
previous_sample = None
# Number of samples in the current fixation
fixation_duration = 0


def gaze_data_callback(gaze_data):
    """
    Process incoming gaze data sample.
    :param gaze_data: New data reading to be handled
    """
    ivt(gaze_data)


def ivt(gaze_data):
    """
    Determine fixation and send result to browser.
    :return:
    """
    global previous_sample, fixation_duration

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

    # If the current fixation exceeds the minimum trigger duration
    if fixation_duration == FIXATION_TRIGGER:
        print("Fixation triggered at {}.".format(s_target))


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


def run_tracker():
    tracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
    input("PRESS ANY KEY TO EXIT SCRIPT.")
    tracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)


if __name__ == '__main__':
    run_tracker()
