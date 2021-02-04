#!/usr/bin/env bash

gibo dump JetBrains Python >.gitignore
{
  echo .idea/sonarlint
  echo .direnv
  echo .python-version
} >>.gitignore
