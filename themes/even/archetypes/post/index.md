---
title: "{{ .File.ContentBaseName | replaceRE "^[0-9]{14}-" "" | replaceRE "-" " " | title }}"
slug: {{ .File.ContentBaseName | replaceRE "^[0-9]{14}-" ""  }}
date: {{ .Date }}
draft: true
---

<!--more-->