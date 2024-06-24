#!/usr/bin/env python2

import math, json, colorsys
from gimpfu import *

filenameDataBuf = "/tmp/eshutter.tmp"

gettext.install("gimp20-python", gimp.locale_directory, unicode=True)



def EshutterCapture(image, layer):
	
	# get the region selected by the user
	selectionDefined, x1, y1, x2, y2 = pdb.gimp_selection_bounds(image)

	# exit when no region was selected
	if not selectionDefined:
		pdb.gimp_message ("Select a region first.")
		return

	# get the pixel values inside the selected region line by line
	pixels = []
	for y in range(y1, y2):
		for x in range(x1, x2):
			pixel = layer.get_pixel(x, y)
			pixels.append(pixel)

	# save all the data
	eshutData = { 'x1':x1, 'x2':x2, 'y1':y1, 'y2':y2, 'pixels':pixels }
	with open(filenameDataBuf, 'w') as f:
		f.write(json.dumps(eshutData)+'\n')
		f.close()


def correctRgbChannel(origValue, correctionFactor):
	return int(min(origValue * correctionFactor, 255))

def correctPixel(originalPixel, correction):
	correctedPixel = [ correctRgbChannel(originalPixel[0], correction[0]), correctRgbChannel(originalPixel[1], correction[1]), correctRgbChannel(originalPixel[2], correction[2]) ]
	return correctedPixel

def EshutterFix(image, layer, correctIntensity=1, correctionWidth="full", softEdges=1):

	# get the region selected by the user
	selectionDefined, x1, y1, x2, y2 = pdb.gimp_selection_bounds(image)

	# check whether a region was selected by the user
	if not selectionDefined:
		pdb.gimp_message ("Select a region first.")
		return

	# read the saved data
	with open(filenameDataBuf, 'r') as f:
		eshutData = json.load(f)
		f.close()
	pixels = eshutData['pixels']

	# compute the average RGB per row
	avgRGB = []
	iPixelCounter = 0
	for y in range(eshutData['y1'], eshutData['y2']):

		# fetch the pixels within the selection for row "y"
		pixelRow = []
		for x in range(eshutData['x1'], eshutData['x2']):
			pixelRow.append(pixels[iPixelCounter])
			iPixelCounter = iPixelCounter +1

		# compute the average RGB values for this row of pixels
		sumR = sumG = sumB = 0
		lenPixelRow = len(pixelRow)
		for pixel in pixelRow:
			sumR = sumR + pixel[0]
			sumG = sumG + pixel[1]
			sumB = sumB + pixel[2]

		avgRGB.append( [float(sumR)/lenPixelRow, float(sumG)/lenPixelRow, float(sumB)/lenPixelRow] )

	# set up the correction matrix
	corrections = []
	for i in range(len(avgRGB)):
		corrections.append([ 1.0, 1.0, 1.0 ])
	lenCorrections = len(corrections)

	# compute the width of a 10% border
	softBorder = int(0.1 * lenCorrections)

	# compute the intensity correction
	if correctIntensity:
		# compute average intensity
		avgI = []
		for rgb in avgRGB:
			intensity = sum(rgb) / len(rgb)
			avgI.append(intensity)

		# compute top and bottom intensity
		avgItop = avgI[0:softBorder-1]
		avgIbot = avgI[lenCorrections-softBorder:lenCorrections-1]

		iTop    = sum(avgItop) / len(avgItop)
		iBottom = sum(avgIbot) / len(avgIbot)

		# adjust for linear evolution from top to bottom
		for i in range(lenCorrections):
			targetI = iTop + i * (iBottom - iTop) / lenCorrections

			for j in range(len(corrections[i])):
				corrections[i][j] = targetI / avgI[i]

	# compute the color corrections
	for iCorr in range(lenCorrections):
		rgb = avgRGB[iCorr]
		sumRGB = sum(rgb)
		for j in range(len(rgb)):
			corrections[iCorr][j] = corrections[iCorr][j] * sumRGB/(3*rgb[j])
		iCorr = iCorr +1

	# soft edges
	if softEdges:
		# soften the corrections
		for iSoft in range(softBorder):  # distance from the edge
			# correct at the top
			iCorr = iSoft  # index in the corrections array
			#avgCorrection = sum(corrections[iCorr]) / len(corrections[iCorr])
			#softenFactor = avgCorrection * (softBorder-iSoft) / softBorder
			softenFactor = float(iSoft) / float(softBorder)
			for i in range(len(corrections[iCorr])):
				corrections[iCorr][i] = 1 + softenFactor * (corrections[iCorr][i] -1)

			# correct at the bottom
			iCorr = lenCorrections -1 -iSoft
			#avgCorrection = sum(corrections[iCorr]) / len(corrections[iCorr])
			#softenFactor = avgCorrection * (softBorder-iSoft) / softBorder
			for i in range(len(corrections[iCorr])):
				#corrections[iCorr][i] = softenFactor * corrections[iCorr][i]
				corrections[iCorr][i] = 1 + softenFactor * (corrections[iCorr][i] -1)

    # indicates that the process has started
	gimp.progress_init("Fixing " + layer.name + "...")

	# set up an undo group, so the operation will be undone in one step
	pdb.gimp_image_undo_group_start(image)

	# get the layer position
	pos = 0;
	for i in range(len(image.layers)):
		if(image.layers[i] == layer):
			pos = i

	# create a new layer to save the results (otherwise is not possible to undo the operation)
	newLayer = pdb.gimp_layer_new_from_drawable(layer, image)
	image.add_layer(newLayer, pos)
	layerName = layer.name
    
	# apply the corrections
	heightSelection = y2-y1

	if correctionWidth=="full":
		xRange = range(layer.width)
	else:
		xRange = range(x1, x2)

	for y in range(y1, y2):
		iCorrection = lenCorrections * (y-y1) / heightSelection
		correction = corrections[iCorrection]
		for x in xRange:
			originalPixel = layer.get_pixel(x, y)
			correctedPixel = correctPixel(originalPixel, correction)
			newLayer.set_pixel(x, y, correctedPixel)

		gimp.progress_update(float(y-y1) / float(y2-y1))

	# update the new layer
	newLayer.flush()
	newLayer.merge_shadow(True)
	newLayer.update(0, 0, newLayer.width, newLayer.height)
	
	# remove the old layer
	image.remove_layer(layer)
	
	# change the name of the new layer (two layers can not have the same name)
	newLayer.name = layerName

	# close the undo group
	pdb.gimp_image_undo_group_end(image)

    # end progress
	pdb.gimp_progress_end()


register(
	"python_fu_eshutter_capture",  # plugin name
	N_("Capture the pixels inside the selection"),  # description
	"Capture the pixels inside the selection",  # help
	"Wim Mees",  # author
	"Wim Mees",  # copyright
	"2024",  # date
	N_("_Capture..."),  # menu path
	"*RGB*, GRAY*",  # permitted image formats
	[
		(PF_IMAGE, "image", "Input image", None),
		(PF_DRAWABLE, "drawable", "Input drawable", None)
	],   # plugin parameters
	[],  # memory buffer for return value
	EshutterCapture,
	menu="<Image>/Filters/Eshutter",
    domain=("gimp20-python", gimp.locale_directory)
	)

register(
	"python_fu_eshutter_fix",  # plugin name
	N_("Fix the fringes"),  # description
	"Fix the fringes inside the selected region, caused by the electronic shutter",  # help
	"Wim Mees",  # author
	"Wim Mees",  # copyright
	"2024",  # date
	N_("_Fix..."),  # menu path, was: "<Image>/Filters/Artistic/EshutterAnalyze"
	"*RGB*, GRAY*",  # permitted image formats
	[
		(PF_IMAGE, "image", "Input image", None),
		(PF_DRAWABLE, "drawable", "Input drawable", None),
		(PF_TOGGLE, "correctIntensity", "correct intensity", 1),
		(PF_RADIO, "correctionWidth", "correction width", "selection", (("selection", "selection"), ("full", "full"))),
		(PF_TOGGLE, "softEdges", "soft edges", 1)
	],   # plugin parameters
	[],  # memory buffer for return value
	EshutterFix,
	menu="<Image>/Filters/Eshutter",
    domain=("gimp20-python", gimp.locale_directory)
	)

main()



