import io
import math
import os
from textwrap import wrap
from typing import Mapping

import requests
from wand.color import Color
from wand.drawing import Drawing
from wand.image import Image

BASE_URL = 'https://garyatrics.com/gow_assets'

FONTS = {
    'opensans': r'fonts/OpenSans-Regular.ttf',
    'raleway': r'fonts/Raleway-Regular.ttf',
}


def download_image(path):
    cache_path = '.cache'
    cache_filename = os.path.join(cache_path, path)
    if os.path.exists(cache_filename):
        f = open(cache_filename, 'rb')
    else:
        url = f'{BASE_URL}/{path}'
        r = requests.get(url)
        f = io.BytesIO(r.content)
        cache_subdir = os.path.dirname(cache_filename)
        if not os.path.exists(cache_subdir):
            os.makedirs(cache_subdir)
        with open(cache_filename, 'wb') as cache:
            cache.write(f.read())
        f.seek(0)
    img = Image(file=f)
    img.alpha_channel = True
    f.close()
    return img


def scale_down(width, height, max_size):
    ratio = width / height
    if width > height:
        return max_size, round(max_size / ratio)
    else:
        return round(ratio * max_size), max_size


def word_wrap(image, draw, text, roi_width, roi_height):
    """Break long text to multiple lines, and reduce point size
    until all text fits within a bounding box."""
    mutable_message = text
    iteration_attempts = 100

    def eval_metrics(txt):
        """Quick helper function to calculate width/height of text."""
        metrics = draw.get_font_metrics(image, txt, True)
        return metrics.text_width, metrics.text_height

    while draw.font_size > 0 and iteration_attempts:
        iteration_attempts -= 1
        width, height = eval_metrics(mutable_message)
        if height > roi_height:
            draw.font_size -= 0.75  # Reduce pointsize
            mutable_message = text  # Restore original text
        elif width > roi_width:
            columns = len(mutable_message)
            while columns > 0:
                columns -= 1
                mutable_message = '\n'.join(wrap(mutable_message, columns))
                wrapped_width, _ = eval_metrics(mutable_message)
                if wrapped_width <= roi_width:
                    break
            if columns < 1:
                draw.font_size -= 0.75  # Reduce pointsize
                mutable_message = text  # Restore original text
        else:
            break
    if iteration_attempts < 1:
        raise RuntimeError("Unable to calculate word_wrap for " + text)
    return mutable_message


class WeeklyPreview:
    def __init__(self, data):
        self.data = data
        self.img = None
        self.weapon = None
        self.spacing = 0

    def render_background(self):
        self.img = download_image(self.data['background'])
        self.spacing = self.img.width // 2 - 980
        gow_logo = download_image(self.data['gow_logo'])
        ratio = gow_logo.width / gow_logo.height
        gow_logo.resize(round(200 * ratio), 200)
        switch_logo = Image(filename='switch_logo.png')
        ratio = switch_logo.width / switch_logo.height
        switch_logo.resize(round(100 * ratio), 100)
        with Drawing() as draw:
            color = Color('rgba(0, 0, 0, 0.7)')
            draw.fill_color = color
            draw.rectangle(0, 0, self.img.width, 300)
            draw.composite(operator='atop',
                           left=(300 - gow_logo.height) // 2, top=(300 - gow_logo.height) // 2,
                           width=gow_logo.width, height=gow_logo.height,
                           image=gow_logo)
            if self.data['switch']:
                draw.composite(operator='atop',
                               left=(300 - switch_logo.height) // 2 - 15, top=300 - switch_logo.height - 15,
                               width=switch_logo.width, height=switch_logo.height,
                               image=switch_logo)
            draw.fill_color = Color('white')
            draw.font_size = 100
            draw.text_antialias = True
            draw.font = FONTS['raleway']
            draw.text(450, 200, f'{self.data["texts"]["soulforge"]}: {self.data["date"]}')

            kingdom_logo = download_image(self.data['kingdom_logo'])
            kingdom_width, kingdom_height = scale_down(kingdom_logo.width, kingdom_logo.height, 220)
            kingdom_logo.resize(kingdom_width, kingdom_height)
            draw.composite(operator='atop',
                           left=self.img.width - kingdom_width - 15, top=15,
                           width=kingdom_width, height=kingdom_height,
                           image=kingdom_logo
                           )
            draw.font_size = 40
            draw.text_alignment = 'center'
            kingdom = word_wrap(self.img, draw, self.data['kingdom'], kingdom_width + 10, int(1.5 * draw.font_size))
            x = self.img.width - kingdom_width // 2 - 15
            y = kingdom_logo.height + int(1.5 * draw.font_size)
            draw.text(x, y, kingdom)

            draw(self.img)

    def get_box_coordinates(self, box_number):
        outer_spacing_percentage = 3
        inner_spacing_percentage = 1
        vertical_spacing_percentage = 10
        vertical_spacing = vertical_spacing_percentage * self.img.height / 100
        height = self.img.height - 300 - 2 * vertical_spacing
        top = round(250 + vertical_spacing)

        outer_spacing = outer_spacing_percentage * self.img.width / 100
        inner_spacing = inner_spacing_percentage * self.img.width / 100
        width = round((self.img.width - 2 * outer_spacing - 2 * inner_spacing) / 3)

        left = round(outer_spacing + box_number * (width + inner_spacing))

        return left, top, width, height

    def render_soulforge_screen(self):
        left, top, width, height = self.get_box_coordinates(1)

        self.weapon = download_image(self.data['filename'])
        ratio = self.weapon.width / self.weapon.height
        self.weapon.resize(round(180 * ratio), 180)
        with Drawing() as draw:
            draw.fill_color = Color('none')
            draw.stroke_color = Color('rgb(16, 17, 19)')
            draw.stroke_width = 20
            draw.circle(origin=(self.weapon.width // 2, self.weapon.height // 2),
                        perimeter=(self.weapon.width // 2, -draw.stroke_width // 2))
            draw.border_color = draw.stroke_color
            try:
                draw.matte(0, 0, 'filltoborder')
                draw.matte(self.weapon.width - 1, 0, 'filltoborder')
            except AttributeError:
                draw.alpha(0, 0, 'filltoborder')
                draw.alpha(self.weapon.width - 1, 0, 'filltoborder')
            draw(self.weapon)

        with Drawing() as draw:
            draw.fill_color = Color('rgba(0, 0, 0, 0.7)')
            rarity_color = ','.join([str(c) for c in self.data['rarity_color']])
            draw.stroke_color = Color(f'rgb({rarity_color})')
            draw.stroke_width = 8
            draw.rectangle(left, top, left + width, top + height, radius=40)

            draw.fill_color = Color('rgb(35, 39, 38)')
            draw.stroke_color = draw.fill_color
            draw.stroke_width = 0
            draw.circle((left + 300, top + 350), (left + 300, top + 235))
            slot_angles = [48 * x - 258 for x in range(1, 7)]

            requirement_objects = self.extract_requirements()

            for i, angle in enumerate(slot_angles):
                draw.fill_color = Color('rgb(35, 39, 38)')
                draw.stroke_color = draw.fill_color
                hypotenuse = 210
                rad_angle = 2 * math.pi * (90 + angle) / 360
                center = left + 300 - hypotenuse * math.sin(rad_angle), top + 350 - hypotenuse * math.cos(rad_angle)
                perimeter = (center[0], center[1] + 115 // 2)
                draw.stroke_width = 10
                draw.line((left + 300, top + 350), center)
                draw.stroke_width = 0
                draw.circle(center, perimeter)
                if requirement_objects[i]:
                    filename, amount = requirement_objects[i]
                    requirement_img = download_image(filename)
                    max_size = 70
                    r_width, r_height = scale_down(*requirement_img.size, max_size)
                    draw.composite(operator='atop',
                                   left=center[0] - r_width // 2, top=center[1] - r_height // 2,
                                   width=r_width, height=r_height,
                                   image=requirement_img)
                    draw.text_antialias = True
                    draw.stroke_color = Color('rgb(10, 199, 43)')
                    draw.stroke_width = 0
                    draw.fill_color = draw.stroke_color
                    draw.font_size = 35
                    draw.font = FONTS['opensans']
                    draw.text_alignment = 'center'
                    draw.text(round(center[0]), round(center[1] + max_size), f'{amount:,.0f}')

            draw.composite(operator='atop',
                           left=left + 182, top=top + 260,
                           width=self.weapon.width, height=self.weapon.height,
                           image=self.weapon)
            draw.fill_color = Color('none')
            draw.stroke_color = Color('rgb(35, 39, 38)')
            draw.stroke_width = 20
            draw.circle((left + 300, top + 350), (left + 300, top + 250))

            draw.stroke_color = Color('rgb(16, 17, 19)')
            draw.stroke_width = 10
            draw.circle((left + 300, top + 350), (left + 300, top + 255))

            draw.fill_color = Color('white')
            draw.stroke_color = Color('white')
            draw.font = FONTS['opensans']
            draw.font_size = 60
            draw.stroke_width = 0
            draw.text_alignment = 'center'
            draw.text_antialias = True
            name = word_wrap(self.img, draw, self.data['name'], width, int(1.5 * draw.font_size))
            draw.text(left + width // 2, top + 80 - int(60 - draw.font_size), name)

            draw.font_size = 30
            draw.font = FONTS['raleway']
            draw.text_alignment = 'center'
            draw.fill_color = Color('white')
            crafting_message = word_wrap(self.img, draw, self.data["texts"]["in_soulforge"], width - 20, 100)
            text_top = round(top + height - draw.font_size * 2)
            draw.text(left + width // 2, text_top, crafting_message)

            draw(self.img)

    def render_affixes(self):
        affix_icon = download_image(self.data['affix_icon'])
        gold_medal = download_image(self.data['gold_medal'])
        mana = download_image(self.data['mana_color'])
        with Drawing() as draw:
            draw.fill_color = Color('rgba(0, 0, 0, 0.7)')
            draw.stroke_width = 0
            left, top, width, height = self.get_box_coordinates(0)
            draw.rectangle(left, top, left + width, top + height, radius=40)

            draw.composite(operator='atop',
                           left=left + 20, top=top + 8,
                           width=mana.width, height=mana.height,
                           image=mana)
            draw.composite(operator='atop', left=left + 10, top=top + 5,
                           width=gold_medal.width, height=gold_medal.height,
                           image=gold_medal)
            draw.font_size = 70
            draw.stroke_width = 0
            draw.text_antialias = True
            draw.text_alignment = 'center'
            draw.font = FONTS['opensans']
            mana_x = left + 20 + mana.width // 2
            mana_y = round(top + 8 + mana.height / 2 + draw.font_size / 3)
            draw.fill_color = Color('black')
            draw.text(mana_x + 2, mana_y + 2, str(self.data['mana_cost']))
            draw.fill_color = Color('white')
            draw.text(mana_x, mana_y, str(self.data['mana_cost']))

            draw.fill_color = Color('white')
            draw.stroke_color = Color('none')
            draw.text_alignment = 'left'
            draw.stroke_width = 0
            base_size = 30
            draw.font_size = base_size
            draw.font = FONTS['raleway']
            description = word_wrap(self.img, draw, self.data['description'], 420, height // 3)
            draw.text(left + 160, top + 25 + 3 * base_size, description)

            draw.text_alignment = 'right'
            draw.font_size = 2 * base_size

            draw.fill_color = Color('white')
            draw.text(left + width - 10, top + 25 + base_size, self.data['type'])

            offset = 375
            x = left + width
            for affix in self.data['affixes']:
                my_affix = affix_icon.clone()
                color_code = ','.join([str(c) for c in affix['color']])
                my_affix.colorize(color=Color(f'rgb({color_code})'), alpha=Color('rgb(100%, 100%, 100%)'))

                draw.fill_color = Color('white')
                draw.composite(operator='atop',
                               left=x - 65, top=top + offset - 3 * base_size // 4,
                               width=affix_icon.width, height=affix_icon.height,
                               image=my_affix)
                draw.font_size = base_size
                draw.font = FONTS['raleway']
                draw.text(x - 70, top + offset, affix['name'])
                draw.font_size = 3 * base_size // 5
                draw.font = FONTS['opensans']
                description = word_wrap(self.img, draw, affix['description'], width - 80, base_size + 10)
                draw.text(x - 70, top + offset + base_size - 5, description)
                offset += 2 * base_size

            draw.font_size = 30
            margin = 100
            box_width = 80
            item_count = len(list(self.data['stat_increases'].values()))
            distance = round((600 - item_count * box_width - 2 * margin) / (item_count - 1))
            icon_top = round(height - 70)
            for i, (stat, increase) in enumerate(self.data['stat_increases'].items()):
                icon_left = left + margin + i * (box_width + distance)
                stat_icon = download_image(self.data['stat_icon'].format(stat=stat))
                width, height = scale_down(*stat_icon.size, max_size=50)
                stat_icon.resize(width=width, height=height)
                draw.text(icon_left + 70, top + icon_top + int(1.1 * draw.font_size), str(increase))
                draw.composite(operator='atop',
                               left=icon_left, top=top + icon_top,
                               width=stat_icon.width, height=stat_icon.height,
                               image=stat_icon
                               )
            draw(self.img)

    def render_farming(self):
        with Drawing() as draw:
            left, top, width, height = self.get_box_coordinates(2)

            draw.fill_color = Color('rgba(0, 0, 0, 0.7)')
            draw.stroke_width = 0
            draw.rectangle(left, top, left + width, top + height, radius=40)

            base_size = 35
            draw.font_size = 12 * base_size / 7
            draw.text_antialias = True
            draw.fill_color = Color('white')
            draw.font = FONTS['raleway']
            draw.text(left + 30, top + 25 + base_size, self.data['texts']['resources'])

            draw.font = FONTS['opensans']
            draw.font_size = base_size
            heading = f'{self.data["texts"]["dungeon"]} &\n{self.data["texts"]["kingdom_challenges"]}'
            draw.text(left + 30, top + 25 + 2 * base_size, heading)

            offset = 5 * base_size
            draw.font_size = 30
            draw.font = FONTS['raleway']
            for jewel in self.data['requirements']['jewels']:
                jewel_icon = download_image(jewel['filename'])
                jewel_width, jewel_height = scale_down(jewel_icon.width, jewel_icon.height, 50)
                jewel_icon.resize(width=jewel_width, height=jewel_height)
                draw.composite(operator='atop',
                               left=left + 25, top=top + offset + round(1.5 * draw.font_size),
                               width=jewel_width, height=jewel_height,
                               image=jewel_icon)
                kingdoms = ', '.join(jewel['kingdoms'])

                message_lines = [
                    f'x100 {jewel["available_on"]}: {self.data["texts"]["dungeon_battles"]}',
                    f'x100 {jewel["available_on"]}: {self.data["texts"]["gem_bounty"]} ({self.data["texts"]["n_gems"]})',
                    f'x140 {self.data["texts"]["tier_8"]} {self.data["texts"]["kingdom_challenges"]}:\n{kingdoms}'
                ]
                message = '\n'.join(
                    [word_wrap(self.img, draw, m, width - 2 * jewel_width,
                               7 * (height - 2.5 * base_size) / base_size) for m in
                     message_lines])

                draw.text(left + 25 + 55, top + 30 + offset, message)
                offset += round(2.5 * base_size + int(draw.font_size) * len(message.split('\n')))
            draw(self.img)

    def draw_watermark(self):
        with Drawing() as draw:
            avatar = Image(filename='hawx_transparent.png')
            max_size = 100
            width, height = scale_down(*avatar.size, max_size)
            draw.composite(operator='atop',
                           left=self.img.width - width - 10, top=self.img.height - height - 10,
                           width=width, height=height,
                           image=avatar)

            draw.font_size = 30
            draw.font = FONTS['raleway']
            draw.text_alignment = 'right'
            draw.text_antialias = True
            legal_notice = 'Produced by Hawx & Gary.\nNo redistribution without this notice.'
            draw.fill_color = Color('black')
            draw.text(self.img.width - width - 18, self.img.height - 2 - 2 * int(draw.font_size), legal_notice)
            draw.text(self.img.width - width - 18, self.img.height + 2 - 2 * int(draw.font_size), legal_notice)
            draw.text(self.img.width - width - 18, self.img.height - 2 + 2 * int(draw.font_size), legal_notice)
            draw.text(self.img.width - width - 18, self.img.height + 2 + 2 * int(draw.font_size), legal_notice)
            draw.fill_color = Color('white')
            draw.text(self.img.width - width - 20, self.img.height - 2 * int(draw.font_size), legal_notice)
            draw(self.img)

    def save_image(self):
        self.img.format = 'png'
        self.img.save(filename='test.png')

    def extract_requirements(self) -> Mapping[str, str]:
        result = [None for _ in range(6)]
        souls = 'Commonrewards_icon_soul_small_full.png'
        result[3] = (souls, self.data['requirements'][souls])
        celestials = 'Runes_Rune39_full.png'
        diamonds = 'Runes_JewelDiamond_full.png'
        jewels = self.data['requirements']['jewels']
        if len(jewels) == 1:
            result[4] = (diamonds, self.data['requirements'][diamonds])
            result[2] = (jewels[0]['filename'], jewels[0]['amount'])
            result[1] = (celestials, self.data['requirements'][celestials])
        elif len(self.data['requirements']['jewels']) == 2:
            result[5] = (celestials, self.data['requirements'][celestials])
            result[2] = (jewels[0]['filename'], jewels[0]['amount'])
            result[4] = (jewels[1]['filename'], jewels[1]['amount'])
            result[1] = (diamonds, self.data['requirements'][diamonds])
        return result


def render_all(result):
    overview = WeeklyPreview(result)
    overview.render_background()
    overview.render_soulforge_screen()
    overview.render_affixes()
    overview.render_farming()
    overview.draw_watermark()

    return io.BytesIO(overview.img.make_blob('png'))
