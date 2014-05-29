#!/usr/bin/env python

import time
import os
import numpy as np
import cv2
import cv2.cv as cv
from common import clock, draw_str
import argparse
import glob

def perform_match(img, snout):
    ret, threshimg = cv2.threshold(img, 90, 255, 0)
    cv2.imshow("thresh", threshimg)
    matchres = cv2.matchTemplate(threshimg, snout, cv2.TM_CCOEFF_NORMED)
    (min_x, max_x, minloc, maxloc) = cv2.minMaxLoc(matchres)
    (x, y) = maxloc

    snout_w = snout.shape[1]
    snout_h = snout.shape[0]

    return (max_x, (x, y), (x + snout_w, y + snout_h))

def template_match(img, vis, snout, flipped_snout):
    res, p1, p2 = perform_match(img, snout)

    if res < 0.8:
        print "Flipping"
        res, p1, p2 = perform_match(img, flipped_snout)

    cv2.rectangle(vis, p1, p2, (255, 255, 0), 2)

    print(" Template match: %s" % (res,))

def detect(img, cascade, minsize):
    rects = cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=3, minSize=minsize, flags = cv.CV_HAAR_SCALE_IMAGE)
    if len(rects) == 0:
        return []
    rects[:,2:] += rects[:,:2]
    return rects

def draw_rects(img, rects, color):
    for x1, y1, x2, y2 in rects:
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

if __name__ == '__main__':
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--cascade", metavar = "CASCADE", 
                    help = "The path to the cascade xml file.")

    parser.add_argument("--show", action = "store_true",
                    help = "Show the images while iterating over them.")

    parser.add_argument("--pause_fail", action = "store_true",
                    help = "Pause on failed match.")

    parser.add_argument("--pause_ok", action = "store_true",
                    help = "Pause on ok match")

    parser.add_argument("--min_height", metavar = "HEIGHT", type = int,
                    help = "The minimum height of a match.", default = 24)

    parser.add_argument("--min_width", metavar = "WIDTH", type = int,
                    help = "The minimum widht of a match.", default = 24)

    parser.add_argument("--frame_delay", metavar = "SECONDS", type = float,
                    help = "Delay this many seconds between images.", default = 0.0)

    parser.add_argument("--snout", metavar = "SNOUTIMAGE",
                    help = "The snout image.")

    parser.add_argument("images", metavar = "IMAGE", nargs = "+",
                    help = "The Catcierge match images to test. If a directory is specied, all .png files in that directory are used.")

    args = parser.parse_args()

    if args.snout:
        snout_img_tmp = cv2.imread(args.snout)
        snout_img_gray = cv2.cvtColor(snout_img_tmp, cv2.COLOR_BGR2GRAY)
        ret, snout_img = cv2.threshold(snout_img_gray, 90, 255, 0)
        flipped_snout_img = cv2.flip(snout_img, 1)

    cascade = cv2.CascadeClassifier(args.cascade)
    #nested = cv2.CascadeClassifier(nested_fn)

    image_paths = []

    for img_path in args.images:
        if os.path.isdir(img_path):
            image_paths += glob.glob(img_path + "/*.png")
        else:
            image_paths.append(img_path)

    img_count = 0
    match_count = 0
    w_sum = 0
    h_sum = 0

    for img_path in image_paths:
        print("%s" % img_path)
        img = cv2.imread(img_path)
        if img == None:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_eqhist = cv2.equalizeHist(gray)

        t = clock()
        rects = detect(gray_eqhist, cascade, (args.min_width, args.min_height))
        match_ok = (len(rects) > 0)
        vis = img.copy()
        draw_rects(vis, rects, (0, 255, 0))
        print("Found %d matches" % len(rects))

        for x1, y1, x2, y2 in rects:
            roi = gray[y1:y2, x1:x2]
            vis_roi = vis[y1:y2, x1:x2]
            w = (x2 - x1)
            h = (y2 - y1)
            w_sum += w
            h_sum += h

            if args.snout:
                template_match(roi, vis_roi, snout_img, flipped_snout_img)

            draw_str(vis, (20, 40), "w: %d h: %d" % (w, h))
        dt = clock() - t

        draw_str(vis, (20, 20), 'time: %.1f ms' % (dt*1000))

        show_on_ok = (match_ok and args.pause_ok)
        show_on_fail = (not match_ok and args.pause_fail)

        if args.show or show_on_ok or show_on_fail:
            cv2.imshow('catcierge', vis)

        img_count += 1

        time.sleep(args.frame_delay)

        if match_ok:
            match_count += 1

            if args.pause_ok:
                if 0xFF & cv2.waitKey(0) == 27:
                    break
        elif args.pause_fail:
            if 0xFF & cv2.waitKey(0) == 27:
                break

        if 0xFF & cv2.waitKey(5) == 27:
            break

    if img_count > 0:
        print("%d of %d matches ok (%d)" % (match_count, img_count, float(match_count) / img_count))

        w_avg = float(w_sum) / img_count
        h_avg = float(h_sum) / img_count
        print("(%f, %f) average size of match" % (w_avg, h_avg))
    else:
        print "No images specified ..."

    #cv2.waitKey(0)
    cv2.destroyAllWindows()
