from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'templates/components/car_card.html';text=path.read_text(encoding='utf8')
for old,new in [('image.display_url','image.card_url'),('image.srcset','image.card_srcset'),('image.width','image.card_display_width'),('image.height','image.card_display_height')]:text=text.replace(old,new)
path.write_text(text,encoding='utf8')
path=root/'templates/catalog.html';text=path.read_text(encoding='utf8');text=text.replace('{% block body_attrs %}data-page-event="filter_cars"{% endblock %}','');path.write_text(text,encoding='utf8')
path=root/'templates/booking.html';text=path.read_text(encoding='utf8');text=text.replace(' data-event="booking_start"','');path.write_text(text,encoding='utf8')
print('Dedicated responsive card images enabled; duplicate analytics triggers removed.')
