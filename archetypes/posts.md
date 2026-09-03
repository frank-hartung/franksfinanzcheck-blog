---
title: "{{ replace .File.ContentBaseName "-" " " | title }}"
description: ""
date: {{ .Date }}
lastmod: {{ .Date }}
draft: true
author: "Frank Hartung"
tags: []
categories: ["Ratgeber"]
pillar: ""
keywords: []
kurzantwort: ""
pinwand: "Finanzen | Spartipps & Tarifvergleiche"
pin_title: "{{ replace .File.ContentBaseName "-" " " | title }}"
pin_description: ""
cover:
  image: "images/covers/{{ .File.ContentBaseName }}.jpg"
  alt: "{{ replace .File.ContentBaseName "-" " " | title }}"
  caption: "Tipp von FranksFinanzcheck"
---
