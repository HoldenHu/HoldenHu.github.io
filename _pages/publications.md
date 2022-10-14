---
layout: page
permalink: /publications/
title: publications
description: Strive not to be a success, but rather to be of value.
years: [2022]
nav: true
---

<div class="publications">

{% for y in page.years %}
  <h2 class="year">{{y}}</h2>
  {% bibliography -f papers -q @*[year={{y}}]* %}
{% endfor %}

</div>
