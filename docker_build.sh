#!/usr/bin/env bash
(
  #
  # Builds image with default repo and tag name.
  #

  # Set cwd
  unset CDPATH
  cd "$( dirname "${BASH_SOURCE[0]}" )"

	docker build --no-cache --tag flywheel/hcp-struct .

)