from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'templates/car_detail.html';text=path.read_text(encoding='utf8')
text=text.replace("{% if car.description %}<div class=\"prose\">{{ car|tr:'description'|richtext }}</div>{% endif %}","{% with description=car|tr:'description' %}{% if description %}<div class=\"prose\">{{ description|richtext }}</div>{% endif %}{% endwith %}")
path.write_text(text,encoding='utf8')
path=root/'templates/catalog.html';text=path.read_text(encoding='utf8')
text=text.replace("{% if category.description %}<div class=\"prose section\">{{ category|tr:'description'|richtext }}</div>{% endif %}","{% if category %}{% with content=category|tr:'description' %}{% if content %}<div class=\"prose section\">{{ content|richtext }}</div>{% endif %}{% endwith %}{% endif %}")
path.write_text(text,encoding='utf8')
path=root/'templates/base.html';text=path.read_text(encoding='utf8')
old="<a href=\"{{ '/'|local_url }}#faq\">FAQ</a></nav>"
text=text.replace(old,"<a href=\"{{ '/'|local_url }}#faq\">FAQ</a><a href=\"{{ '/contacts/'|local_url }}\">{% trans 'Контакты' %}</a></nav>")
path.write_text(text,encoding='utf8')
print('Localized CMS content and desktop contacts link updated.')
