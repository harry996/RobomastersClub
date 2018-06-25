import numpy as np
import cv2
import glob
import matplotlib.pyplot as plt


def load_image(file_path,file_name, width=1280, height=720):

    # load the image with picture's name and path
    image = cv2.imread(file_path + file_name)

    if image is not None:
        # resize to specific resolution
        image = cv2.resize(image, (width, height))
        # change it to RGB image
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image
    else:
        print("image not loaded")

#convert pic to binary
def rgb_select(image, thresh=(0, 255), color='r'):
    if color == 'b':
        color_channel = image[:,:,2]
    elif color == 'r':
        color_channel = image[:,:,0]
    binary_output = np.zeros_like(color_channel)
    binary_output[(color_channel > thresh[0]) & (color_channel <= thresh[1])] = 1
    return binary_output



# filter 1
# input list to store required ellipse, all contours from image
# only choose contours' area that are greater than 40
# fitEllipse
# will return a rotated rect
# ellipse--> ((xc,yc),(a,b),theta)
        #xc : x coordinate of the center
        # yc : y coordinate of the center
        # a : width
        # b : height
        # theta : rotation angle
# output list that stored required ellipse
def get_ellipse(all_element_list,contours):

    for i in contours:

        area = cv2.contourArea(i)
        if area > 50:
            ellipse = cv2.fitEllipse(i)
            all_element_list.append(ellipse)



    # list of ellipses which area are greater than
    return all_element_list



def slope(x1, y1, x2, y2):
    return (y2-y1)/(x2-x1)



# pair up ellipses
# input: list to store required pairs, list of ellipse that pass perivous fileter
# output: list of pairs of ellipses
# [(elp1,elps2),(elps3,elps4)....]
# ellipses have similar width that are similar, within 5
# ellipses have similar rotation angle: after substraction, within -5,5 or not in -175,175
# ellipses x distances are in range of (60,300)
def get_pairs(pairs,all_element_list):


    itr = len(all_element_list)-1
    for i in range(0, itr):
        for j in range(i+1,itr+1):
            # angle within 5 degree
            if (int(all_element_list[i][2]-all_element_list[j][2]) in range(-10,10)) or (int(all_element_list[i][2]-all_element_list[j][2]) not in range(-170,170)):
# #               x distance between centers inrange 60,300
                if (abs(int(all_element_list[i][0][0]-all_element_list[j][0][0])) in range(60,180)) and (abs(int(all_element_list[i][0][1]-all_element_list[j][0][1]) ) in range(0,80) ):
#                     length two ellipse's semi axes are similar, ie the height is similar
                    if(abs(int(all_element_list[i][1][1]-all_element_list[j][1][1])) < 15) or ((abs(int(all_element_list[i][1][1]-all_element_list[j][1][1])) in range (14,24) ) and int(all_element_list[i][1][1]+all_element_list[j][1][1])<90 ) :
                        # the paired up ellipse's rotation angle should not be similar to their centers' connection's slope (to avoid false positive when two lights are on the same line)
                        # slpoe of line that connected two ellipse's connection
                        slp = slope(all_element_list[i][0][0],all_element_list[i][0][1],all_element_list[j][0][0],all_element_list[j][0][1])
                        deg = 90 + np.arctan(slp)*57.3
                        # difference is greater than 30 degree
                        if((abs(deg - all_element_list[i][-1] ) > 30 ) and (abs(deg - all_element_list[j][-1] ) > 30 )  ):
                            # add paired up ellipsee to list
                            pairs.append([all_element_list[i],all_element_list[j]])
    return pairs




# limit to only one pair
# get the mid point coordinate between two ellipse centers in a pair
# return the mid points' coor in aim_list

def get_aim(aim_list,pairs):

    # equal to sum of heights of ellipse in a pair
    maxSum = 0
    x =0
    y =0
    for i in pairs:
        if maxSum < (i[0][1][1]+i[1][1][1]):
            maxSum = i[0][1][1]+i[1][1][1]
            x = int((i[0][0][0]+i[1][0][0])/2)
            y = int((i[0][0][1]+i[1][0][1])/2)
    aim =(x,y)
    aim_list.append(aim)

    return aim_list

# enhanced method to get aiming, when no pair had returned from get paired
# use one single light to get an approxmate target
# return target's coor in aim_list
def enhanced_get_aim(aim_list,all_element_list):
    ellipse_list = []
    for i in all_element_list:
        if int(i[-1]) not in range(20,165):
            ellipse_list.append(i)
    if len(ellipse_list)>1:
        maxArea = 0
        for i in ellipse_list:
            if maxArea < i[1][1] * i [1][0]:
                maxArea = i[1][1] * i [1][0]
                if i[-1] < 90:
                    elp_center = (i[0][0]-40, i[0][1]-15)
                else:
                    elp_center = (i[0][0]+40, i[0][1]-15)
    else:
        if ellipse_list[0][-1] < 90:
            elp_center = (ellipse_list[0][0][0]-40, ellipse_list[0][0][1]-15)
        else:
            elp_center = (ellipse_list[0][0][0]+40, ellipse_list[0][0][1]-15)

    target = (int(elp_center[0]),int(elp_center[1]))
    aim_list.append(target)

    return aim_list




# main function for aiming target
# input: image, from camera or from load_image
# output: list of all targets coordinates: aim_list
def process_image(image):

    #convert to binary pic with only red
    rgb_binary = rgb_select(image, thresh=(66, 255), color='r')

    #im2: binary pic with contours drawn
    #contours: list of groups of points of contour, original contours select from binary pic
    im2, contours, hierarchy = cv2.findContours(rgb_binary,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

    # all_element_list: ellipses that passed filters(restrictions)
    all_element_list = []
    all_element_list = get_ellipse(all_element_list,contours)

    # use list pairs to store all desired paired up ellipse
    pairs = []
    pairs = get_pairs(pairs,all_element_list)

    # list that stores all target coordinates
    aim_list = []
#   if pairs == none
#   then use enhanced_get_aim method to get an approxmate target
    if len(pairs) == 0:
        aim_list = enhanced_get_aim(aim_list,all_element_list)

    else:
        aim_list = get_aim(aim_list,pairs)

    # the final result
    return aim_list


#####################################
# end of program ###################
#####################################









####################
# below part for test only


print("test: start")


# pic path
file_path ='images/'

# list of file number's that want to test
y = [1,9,14,112,334,411,435,444,466,488,490]
for x in y:
    picName = 'sentry_view' + str(x) + '.png'
    image = load_image(file_path,picName)
    temp1 = image.copy()

    ###########################################
    # ideal output: targets' coor           ###
    all_target = process_image(image)       ###
    ###########################################

    # test and print target on temp pic
    for i in all_target:
        print(all_target)
        cv2.circle(temp1,(i[0],i[1]), 20, (0,0,255), -1)
        cv2.putText(temp1,str(x),(500,500), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 255, 255))

    # out put pic with target drawn on
    newFileName = str(x) + '.png'
    cv2.imwrite(newFileName,temp1)


print("test end")
