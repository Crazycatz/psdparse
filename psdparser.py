#!/usr/bin/env python

# This file is part of psdparser.
# 
# Psdparser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Psdparser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Psdparser.  If not, see <http://www.gnu.org/licenses/>.

import logging
#import math
#import os
#import sys
#from stat import *
from struct import unpack, calcsize
from PIL import Image

"""
Header mode field meanings
"""
CHANNEL_SUFFIXES = {
	-2: 'layer mask',
	-1: 'A',
	0: 'R',
	1: 'G',
	2: 'B',
	3: 'RGB',
	4: 'CMYK', 5: 'HSL', 6: 'HSB', 
	9: 'Lab', 11: 'RGB',
	12: 'Lab', 13: 'CMYK',
}

"""
Resource id descriptions
"""
RESOURCE_DESCRIPTIONS = {
	1000: 'PS2.0 mode data',
	1001: 'Macintosh print record',
	1003: 'PS2.0 indexed color table',
	1005: 'ResolutionInfo',
	1006: 'Names of the alpha channels',
	1007: 'DisplayInfo',
	1008: 'Caption',
	1009: 'Border information',
	1010: 'Background color',
	1011: 'Print flags',
	1012: 'Grayscale/multichannel halftoning info',
	1013: 'Color halftoning info',
	1014: 'Duotone halftoning info',
	1015: 'Grayscale/multichannel transfer function',
	1016: 'Color transfer functions',
	1017: 'Duotone transfer functions',
	1018: 'Duotone image info',
	1019: 'B&W values for the dot range',
	1021: 'EPS options',
	1022: 'Quick Mask info',
	1024: 'Layer state info',
	1025: 'Working path',
	1026: 'Layers group info',
	1028: 'IPTC-NAA record (File Info)',
	1029: 'Image mode for raw format files',
	1030: 'JPEG quality',
	1032: 'Grid and guides info',
	1033: 'Thumbnail resource',
	1034: 'Copyright flag',
	1035: 'URL',
	1036: 'Thumbnail resource',
	1037: 'Global Angle',
	1038: 'Color samplers resource',
	1039: 'ICC Profile',
	1040: 'Watermark',
	1041: 'ICC Untagged',
	1042: 'Effects visible',
	1043: 'Spot Halftone',
	1044: 'Document specific IDs',
	1045: 'Unicode Alpha Names',
	1046: 'Indexed Color Table Count',
	1047: 'Transparent Index',
	1049: 'Global Altitude',
	1050: 'Slices',
	1051: 'Workflow URL',
	1052: 'Jump To XPEP',
	1053: 'Alpha Identifiers',
	1054: 'URL List',
	1057: 'Version Info',
	2999: 'Name of clipping path',
	10000: 'Print flags info',
}

MODES = {
	0:  'Bitmap',
	1:  'GrayScale',
	2:  'IndexedColor',
	3:  'RGBColor',
	4:  'CMYKColor',
	5:  'HSLColor',
	6:  'HSBColor',
	7:  'Multichannel',
	8:  'Duotone',
	9:  'LabColor',
	10: 'Gray16',
	11: 'RGB48',
	12: 'Lab48',
	13: 'CMYK64',
	14: 'DeepMultichannel',
	15: 'Duotone16',
}

COMPRESSIONS = {
	0: 'Raw',
	1: 'RLE',
	2: 'ZIP',
	3: 'ZIPPrediction',
}

BLENDINGS = {
	'norm': 'normal',
	'dark': 'darken',
	'mul ': 'multiply',
	'lite': 'lighten',
	'scrn': 'screen',
	'over': 'overlay',
	'sLit': 'soft-light',
	'hLit': 'hard-light',
	'lLit': 'linear-light',
	'diff': 'difference',
	'smud': 'exclusion',
}

PIL_BANDS = {
	'R': 0,
	'G': 1,
	'B': 2,
	'A': 3,
	'L': 0,
}

def INDENT_OUTPUT(depth, msg):
	return ''.join(['	' for i in range(0, depth)]) + msg

class PSDParser():
	
	header = None
	ressources = None
	num_layers = 0
	layers = None
	images = None
	merged_image = None
	
	def __init__(self, filename):
		self.filename = filename
	
	def _pad2(self, i):
		"""same or next even"""
		return (i + 1) / 2 * 2

	def _pad4(self, i):
		"""same or next multiple of 4"""
		return (i + 3) / 4 * 4
	
	def _readf(self, format):
		"""read a strct from file structure according to format"""
		return unpack(format, self.fd.read(calcsize(format)))

	def _skip_block(self, desc, indent=0, new_line=False):
		(n,) = self._readf('>L') # (n,) is a 1-tuple.
		if n:
			self.fd.seek(n, 1) # 1: relative

		if new_line:
			logging.debug('')
		logging.debug(INDENT_OUTPUT(indent, 'Skipped %s with %s bytes' % (desc, n)))
	
	def parse(self):
		logging.debug("Opening '%s'" % self.filename)
		
		self.fd = open(self.filename, 'rb')
		try:
			self.parse_header()
			self.parse_image_resources()
			self.parse_layers_and_masks()
			self.parse_image_data()
		finally:
			self.fd.close()
		
		logging.debug("")
		logging.debug("DONE")
	
	def parse_header(self):
		logging.debug("")
		logging.debug("# Header #")
		
		self.header = {}
		
		C_PSD_HEADER = ">4sH 6B HLLHH"
		(
			self.header['sig'],
			self.header['version'],
			self.header['r0'],
			self.header['r1'],
			self.header['r2'],
			self.header['r3'],
			self.header['r4'],
			self.header['r5'],
			self.header['channels'],
			self.header['rows'],
			self.header['cols'],
			self.header['depth'],
			self.header['mode']
		) = self._readf(C_PSD_HEADER)
		
		self.size = [self.header['rows'], self.header['cols']]
		
		if self.header['sig'] != "8BPS":
			raise ValueError("Not a PSD signature: '%s'" % self.header['sig'])
		if self.header['version'] != 1:
			raise ValueError("Can not handle PSD version:%d" % self.header['version'])
		self.header['modename'] = MODES[self.header['mode']] if 0 <= self.header['mode'] < 16 else "(%s)" % self.header['mode']
		
		logging.debug(INDENT_OUTPUT(1, "channels:%(channels)d, rows:%(rows)d, cols:%(cols)d, depth:%(depth)d, mode:%(mode)d [%(modename)s]" % self.header))
		logging.debug(INDENT_OUTPUT(1, "%s" % self.header))
		
		# Remember position
		self.header['colormodepos'] = self.fd.tell()
		self._skip_block("color mode data", 1)
	
	def parse_image_resources(self):
		def parse_irb():
			"""return total bytes in block"""
			r = {}
			r['at'] = self.fd.tell()
			(r['type'], r['id'], r['namelen']) = self._readf(">4s H B")
			n = self._pad2(r['namelen'] + 1) - 1
			(r['name'],) = self._readf(">%ds" % n)
			r['name'] = r['name'][:-1] # skim off trailing 0byte
			r['short'] = r['name'][:20]
			(r['size'],) = self._readf(">L")
			self.fd.seek(self._pad2(r['size']), 1) # 1: relative
			r['rdesc'] = "[%s]" % RESOURCE_DESCRIPTIONS.get(r['id'], "?")
			logging.debug(INDENT_OUTPUT(1, "Resource: %s" % r))
			logging.debug(INDENT_OUTPUT(1, "0x%(at)06x| type:%(type)s, id:%(id)5d, size:0x%(size)04x %(rdesc)s '%(short)s'" % r))
			self.ressources.append(r)
			return 4 + 2 + self._pad2(1 + r['namelen']) + 4 + self._pad2(r['size'])
		
		logging.debug("")
		logging.debug("# Ressources #")
		self.ressources = []
		(n,) = self._readf(">L") # (n,) is a 1-tuple.
		while n > 0:
			n -= parse_irb()
		if n != 0:
			logging.debug("Image resources overran expected size by %d bytes" % (-n))
	
	def parse_image(self, li, is_layer=True):
		def parse_channel(li, idx, count, rows, cols, depth):
			"""params:
			li -- layer info struct
			idx -- channel number
			count -- number of channels to process ???
			rows, cols -- dimensions
			depth -- bits
			"""
			chlen = li['chlengths'][idx]
			if chlen is not None  and  chlen < 2:
				raise ValueError("Not enough channel data: %s" % chlen)
			if li['chids'][idx] == -2:
				rows, cols = li['mask'].rows, li['mask'].cols
			
			rb = (cols * depth + 7) / 8 # round to next byte
			
			# channel header
			chpos = self.fd.tell()
			(comp,) = self._readf(">H")
			
			if chlen:
				chlen -= 2
			
			pos = self.fd.tell()
			
			# If empty layer
			if cols * rows == 0:
				logging.debug(INDENT_OUTPUT(1, "Empty channel, skiping"))
				return
			
			if COMPRESSIONS.get(comp) == 'RLE':
				logging.debug(INDENT_OUTPUT(1, "Handling RLE compressed data"))
				rlecounts = 2 * count * rows
				if chlen and chlen < rlecounts:
					raise ValueError("Channel too short for RLE row counts (need %d bytes, have %d bytes)" % (rlecounts,chlen))
				pos += rlecounts # image data starts after RLE counts
				rlecounts_data = self._readf(">%dH" % (count * rows))
				for ch in range(count):
					rlelen_for_channel = sum(rlecounts_data[ch * rows:(ch + 1) * rows])
					data = self.fd.read(rlelen_for_channel)
					channel_name = CHANNEL_SUFFIXES[li['chids'][idx]]
					if li['channels'] == 2 and channel_name == 'B': channel_name = 'L'
					p = Image.fromstring("L", (cols, rows), data, "packbits", "L" )
					if is_layer:
						self.images[li['idx']][PIL_BANDS[channel_name]] = p
					else:
						self.merged_image.append(p)
			
			elif COMPRESSIONS.get(comp) == 'Raw':
				logging.debug(INDENT_OUTPUT(1, "Handling Raw compressed data"))
				
				for ch in range(count):
					data = self.fd.read(cols * rows)
					channel_name = CHANNEL_SUFFIXES[li['chids'][idx]]
					if li['channels'] == 2 and channel_name == 'B': channel_name = 'L'
					p = Image.fromstring("L", (cols, rows), data, "raw", "L")
					if is_layer:
						self.images[li['idx']][PIL_BANDS[channel_name]] = p
					else:
						self.merged_image.append(p)
			
			else:
				# TODO: maybe just skip channel...:
				#   f.seek(chlen, SEEK_CUR)
				#   return
				raise ValueError("Unsupported compression type: %s" % COMPRESSIONS.get(comp, comp))
			
			if (chlen is not None) and (self.fd.tell() != chpos + 2 + chlen):
				logging.debug("currentpos:%d should be:%d!" % (f.tell(), chpos + 2 + chlen))
				self.fd.seek(chpos + 2 + chlen, 0) # 0: SEEK_SET
			
			return
		
		if not self.header:
			self.parse_header()
		if not self.ressources:
			self._skip_block("image resources", new_line=True)
			self.ressources = 'not parsed'
		
		logging.debug("")
		logging.debug("# Image: %s/%d #" % (li['name'], li['channels']))
		
		# channels
		if is_layer:
			for ch in range(li['channels']):
				parse_channel(li, ch, 1, li['rows'], li['cols'], self.header['depth'])
		else:
			parse_channel(li, 0, li['channels'], li['rows'], li['cols'], self.header['depth']) 
		return
	
	def parse_layers_and_masks(self):
		
		if not self.header:
			self.parse_header()
		if not self.ressources:
			self._skip_block('image resources', new_line=True)
			self.ressources = 'not parsed'
		
		logging.debug("")
		logging.debug("# Layers & Masks #")
		
		self.layers = []
		self.images = []
		self.header['mergedalpha'] = False
		(misclen,) = self._readf(">L")
		if misclen:
			miscstart = self.fd.tell()
			# process layer info section
			(layerlen,) = self._readf(">L")
			if layerlen:
				# layers structure
				(self.num_layers,) = self._readf(">h")
				if self.num_layers < 0:
					self.num_layers = -self.num_layers
					logging.debug(INDENT_OUTPUT(1, "First alpha is transparency for merged image"))
					self.header['mergedalpha'] = True
				logging.debug(INDENT_OUTPUT(1, "Layer info for %d layers:" % self.num_layers))
				
				if self.num_layers * (18 + 6 * self.header['channels']) > layerlen:
					raise ValueError("Unlikely number of %s layers for %s channels with %s layerlen. Giving up." % (self.num_layers, self.header['channels'], layerlen))
				
				linfo = [] # collect header infos here
				
				for i in range(self.num_layers):
					l = {}
					l['idx'] = i
					
					#
					# Layer Info
					#
					(l['top'], l['left'], l['bottom'], l['right'], l['channels']) = self._readf(">llllH")
					(l['rows'], l['cols']) = (l['bottom'] - l['top'], l['right'] - l['left'])
					logging.debug(INDENT_OUTPUT(1, "layer %(idx)d: (%(left)4d,%(top)4d,%(right)4d,%(bottom)4d), %(channels)d channels (%(cols)4d cols x %(rows)4d rows)" % l))
					
					# Sanity check
					if l['bottom'] < l['top'] or l['right'] < l['left'] or l['channels'] > 64:
						logging.debug(INDENT_OUTPUT(2, "Something's not right about that, trying to skip layer."))
						self.fd.seek(6 * l['channels'] + 12, 1) # 1: SEEK_CUR
						self._skip_block("layer info: extra data", 2)
						continue # next layer
					
					# Read channel infos
					l['chlengths'] = []
					l['chids']  = []
					# - 'hackish': addressing with -1 and -2 will wrap around to the two extra channels
					l['chindex'] = [ -1 ] * (l['channels'] + 2)
					for j in range(l['channels']):
						chid, chlen = self._readf(">hL")
						l['chids'].append(chid)
						l['chlengths'].append(chlen)
						logging.debug(INDENT_OUTPUT(3, "Channel %2d: id=%2d, %5d bytes" % (j, chid, chlen)))
						if -2 <= chid < l['channels']:
							# pythons negative list-indexs: [ 0, 1, 2, 3, ... -2, -1]
							l['chindex'][chid] = j
						else:
							logging.debug(INDENT_OUTPUT(3, "Unexpected channel id %d" % chid))
						l['chidstr'] = CHANNEL_SUFFIXES.get(chid, "?")
					
					# put channel info into connection
					linfo.append(l) 
					
					#
					# Blend mode
					#
					bm = {}
					
					(bm['sig'], bm['key'], bm['opacity'], bm['clipping'], bm['flags'], bm['filler'],
					 ) = self._readf(">4s4sBBBB")
					bm['opacp'] = (bm['opacity'] * 100 + 127) / 255
					bm['clipname'] = bm['clipping'] and "non-base" or "base"
					bm['blending'] = BLENDINGS.get(bm['key'])
					l['blend_mode'] = bm
					
					logging.debug(INDENT_OUTPUT(3, "Blending mode: sig=%(sig)s key=%(key)s opacity=%(opacity)d(%(opacp)d%%) clipping=%(clipping)d(%(clipname)s) flags=%(flags)x" % bm))
					
					# remember position for skipping unrecognized data
					(extralen,) = self._readf(">L")
					extrastart = self.fd.tell()
					
					#
					# Layer mask data
					#
					m = {}
					(m['size'],) = self._readf(">L")
					if m['size']:
						(m['top'], m['left'], m['bottom'], m['right'], m['default_color'], m['flags'],
						 ) = self._readf(">llllBB")
						# skip remainder
						self.fd.seek(m['size'] - 18, 1) # 1: SEEK_CUR
						m['rows'], m['cols'] = m['bottom'] - m['top'], m['right'] - m['left']
					l['mask'] = m
					
					self._skip_block("layer blending ranges", 3)
					
					#
					# Layer name
					#
					(l['namelen'],) = self._readf(">B")
					# - "-1": one byte traling 0byte. "-1": one byte garble.
					# (l['name'],) = readf(f, ">%ds" % (self._pad4(1+l['namelen'])-2)) 
					(l['name'],) = self._readf(">%ds" % (l['namelen'])) 
					
					# Long unicode layer name
					def i16(c):
						return ord(c[1]) + (ord(c[0])<<8)
					
					def i32(c):
						return ord(c[3]) + (ord(c[2])<<8) + (ord(c[1])<<16) + (ord(c[0])<<24)
					
					(signature, key, size,) = self._readf(">4s4s4s") # (n,) is a 1-tuple.
					if key == 'luni':
						namelen = i32(self.fd.read(4))
						namelen += namelen % 2;
						l['name'] = ''
						for count in range(0, namelen - 1):
							l['name'] += unichr(i16(self.fd.read(2)))
					
					logging.debug(INDENT_OUTPUT(3, "Name: '%s'" % l['name']))
					
					# Skip over any extra data
					self.fd.seek(extrastart + extralen, 0) # 0: SEEK_SET
					
					self.layers.append(l)
				
				for i in range(self.num_layers):
					# Empty layer
					try:
						if linfo[i]['rows'] * linfo[i]['cols'] == 0:
							self.images.append(None)
							self.parse_image(linfo[i], is_layer=True)
							continue
					except IndexError: 
						logging.debug(INDENT_OUTPUT(2, "We have a missing layer, did we skip one earlier?."))
						continue
					
					self.images.append([0, 0, 0, 0])
					self.parse_image(linfo[i], is_layer=True)
					if linfo[i]['channels'] == 2:
						l = self.images[i][0]
						a = self.images[i][3]
						self.images[i] = Image.merge('LA', [l, a])
					else:
						self.images[i] = Image.merge('RGBA', self.images[i])
				
			else:
				logging.debug(INDENT_OUTPUT(1, "Layer info section is empty"))
			
			skip = miscstart + misclen - self.fd.tell()
			if skip:
				logging.debug("")
				logging.debug("Skipped %d bytes at end of misc data?" % skip)
				self.fd.seek(skip, 1) # 1: SEEK_CUR
		else:
			logging.debug(INDENT_OUTPUT(1, "Misc info section is empty"))
	
	def parse_image_data(self):
		
		if not self.header:
			self.parse_header()
		if not self.ressources:
			self._skip_block("image resources", new_line=True)
			self.ressources = 'not parsed'
		if not self.layers:
			self._skip_block("image layers", new_line=True)
			self.layers = 'not parsed'
		
		self.merged_image = []
		li = {}
		li['chids'] = range(self.header['channels'])
		li['chlengths'] = [ None ] * self.header['channels'] # dummy data
		(li['name'], li['channels'], li['rows'], li['cols']) = ('merged', self.header['channels'], self.header['rows'], self.header['cols'])
		li['layernum'] = -1
		self.parse_image(li, is_layer=False)
		if li['channels'] == 1:
			self.merged_image = self.merged_image[0]
		elif li['channels'] == 3:
			self.merged_image = Image.merge('RGB', self.merged_image)
		elif li['channels'] == 4:
			self.merged_image = Image.merge('RGBA', self.merged_image)
		else:
			raise ValueError('Unsupported number of channels')

if __name__ == '__main__':
	"""
	Let's get started!
	"""
	
	from optparse import OptionParser
	parser = OptionParser(usage = "usage: %prog [OPTS] PSDFILE.psd")
	po = parser.add_option
	
	# Verbosity
	po('-v', '--verbose', default=False, action='store_true')
	po('-q', '--quiet', default=False, action='store_true')
	
	(OPTS, args) = parser.parse_args()
	
	# The global holder for all the information we really care about
	info = {}
	
	# Set the logger
	level = logging.INFO
	if OPTS.verbose:
		level = logging.DEBUG
	if OPTS.quiet:
		level = logging.WARNING
	
	logging.basicConfig(level=level, format='[DEBUG] %(message)s')
	
	# Run
	if len(args) == 1:
		psd = PSDParser(args[0])
		psd.parse()
		
		import os
		for i in range(len(psd.layers)):
			path='out/'+os.path.basename(args[0])+'/'  
			try:
				os.makedirs(path)
			except:
				pass
			psd.images[i].save(path+psd.layers[i]['name']+'.png', format='PNG')
		
	else:
		parser.print_help()
