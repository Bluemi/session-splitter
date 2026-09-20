#!/bin/bash

case "$1" in
	r)
		shift
		python3 project_name/cli/main.py "$@"
		;;
	t)
		shift
		pytest "$@"
		;;
	*)
		shift
		echo "invalid option: $@"
esac
