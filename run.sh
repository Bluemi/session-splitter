#!/bin/bash

case "$1" in
	r)
		shift
		python3 session-splitter/cli/main.py "$@"
		;;
	t)
		shift
		pytest "$@"
		;;
	*)
		shift
		echo "invalid option: $@"
esac
