#!/usr/bin/env bash

gibo dump JetBrains Python >.gitignore
{
  echo .direnv
  echo .python-version
} >>.gitignore
