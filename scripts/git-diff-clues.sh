#!/bin/sh

SRC=$1
DST=$2

shift
shift

git diff -U0 -G~ \
   --ignore-blank-lines  \
   --ignore-space-at-eol  \
   --ignore-space-change  \
   --ignore-all-space  \
   --src-prefix=$SRC:  \
   --dst-prefix=$DST:  \
   $* | grep '^[+\-]'
