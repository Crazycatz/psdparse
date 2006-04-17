#    This file is part of "psdparse"
#    Copyright (C) 2004-6 Toby Thain, toby@telegraphics.com.au
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by  
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License  
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# This program uses libpng, which in turn uses zlib.
# - on most Linux/UNIX systems, these are shared libraries preinstalled
#   or easily installed with a package manager.
# - on Windows, this makefile is set up to build them from source with MinGW
#   and static link.
# - on OS X, zlib is standard but libpng is not (unless you use a package
#   manager like Fink, http://fink.sourceforge.net/), so we build it ourselves
#   and static link to it.

# for OS X build, download and extract libpng archive, and define path to it:
PNGDIR = ../libpng-1.2.8
# (libpng can be downloaded via http://www.libpng.org/pub/png/libpng.html)

# The following line is only needed where libpng is typically not installed (OS X).
# Otherwise, this line should be commented out (and shared lib will be used):
#LIBPNGA = $(PNGDIR)/libpng.a

# if building with MinGW ('make exe'), extract zlib and libpng to these directories:
ZLIBDIRW32 = ../zlib-1.2.3_w32
PNGDIRW32  = ../libpng-1.2.8_w32
# (zlib can be downloaded via http://www.zlib.net/)

# define MinGW tools
MINGW_CC     = i386-mingw32msvc-gcc
MINGW_AR     = i386-mingw32msvc-ar 
MINGW_RANLIB = i386-mingw32msvc-ranlib

CFLAGS   += -W -Wall -O2
CPPFLAGS += -DDEFAULT_VERBOSE=0

SRC    = main.c writepng.c unpackbits.c
OBJ    = $(patsubst %.c, obj/%.o, $(SRC) )
OBJW32 = $(patsubst %.c, obj_w32/%.o, $(SRC) )

obj/%.o     : %.c ; $(CC)       -o $@ -c $< $(CFLAGS) $(CPPFLAGS)
obj_w32/%.o : %.c ; $(MINGW_CC) -o $@ -c $< $(CFLAGS) $(CPPFLAGS) 

all : psdparse
clean : ; rm -f psdparse psdparse.exe $(OBJ) $(OBJW32)

psdparse : CPPFLAGS += -DDIRSEP=\'/\' -I$(PNGDIR)
psdparse : $(OBJ) $(LIBPNGA)
	$(CC) -o $@ $(filter-out %.a,$^) -L$(PNGDIR) -lz -lpng

# Win32 EXE built by MinGW
exe : psdparse.exe

psdparse.exe : CPPFLAGS += -DDIRSEP=\'\\\\\' -I$(PNGDIRW32) -I$(ZLIBDIRW32)
psdparse.exe : $(ZLIBDIRW32)/libz.a $(PNGDIRW32)/libpng.a $(OBJW32)
	$(MINGW_CC) -s -o $@ $(filter-out %.a,$^) -L$(ZLIBDIRW32) -L$(PNGDIRW32) -lpng -lz

# rule to build libpng

$(PNGDIR)/libpng.a : $(PNGDIR)/scripts/makefile.darwin
	cd $(PNGDIR) && $(MAKE) -f scripts/makefile.darwin libpng.a

# rules to build Win32 libraries

$(PNGDIRW32)/libpng.a : $(PNGDIRW32)/scripts/makefile.gcc
	cd $(PNGDIRW32); \
	$(MAKE) CC=$(MINGW_CC) CPPFLAGS="-I$(ZLIBDIRW32)" AR="$(MINGW_AR) rcs" RANLIB=$(MINGW_RANLIB) \
		-f scripts/makefile.gcc libpng.a

$(ZLIBDIRW32)/libz.a : $(ZLIBDIRW32)/configure
	cd $(ZLIBDIRW32); \
	CC=$(MINGW_CC) AR="$(MINGW_AR) rcs" RANLIB=$(MINGW_RANLIB) ./configure; \
	$(MAKE) libz.a

