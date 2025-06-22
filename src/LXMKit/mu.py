FOREGROUND_RED = 'Ff00'            # Red
FOREGROUND_ORANGE = 'Ffa5'         # Orange
FOREGROUND_YELLOW = 'Fff0'         # Yellow
FOREGROUND_GREEN = 'F0f0'          # Green
FOREGROUND_BLUE = 'F00f'           # Blue
FOREGROUND_INDIGO = 'F309'         # Indigo
FOREGROUND_VIOLET = 'F90f'         # Violet
FOREGROUND_WHITE = 'Ffff'          # White
FOREGROUND_DARK_GREY = 'F555'      # Dark Grey
FOREGROUND_DARKER_GREY = 'F222'    # Darker Grey
FOREGROUND_GREY = 'F888'           # Grey
FOREGROUND_LIGHT_GREY = 'Fbbb'     # Light Grey
FOREGROUND_BLACK = 'F000'          # Black

BACKGROUND_RED = 'Bf00'            # Red
BACKGROUND_ORANGE = 'Bfa5'         # Orange
BACKGROUND_YELLOW = 'Bff0'         # Yellow
BACKGROUND_GREEN = 'B0f0'          # Green
BACKGROUND_BLUE = 'B00f'           # Blue
BACKGROUND_INDIGO = 'B309'         # Indigo
BACKGROUND_VIOLET = 'B90f'         # Violet
BACKGROUND_WHITE = 'Bfff'          # White
BACKGROUND_DARK_GREY = 'B555'      # Dark Grey
BACKGROUND_DARKER_GREY = 'B333'    # Darker Grey
BACKGROUND_GREY = 'B888'           # Grey
BACKGROUND_LIGHT_GREY = 'Bbbb'     # Light Grey
BACKGROUND_BLACK = 'B000'          # Black

CENTER = 'c'
LEFT = 'l'
RIGHT = 'r'
RESET = 'a'
BOLD = 'bold'
ITALIC = 'italic'
UNDERLINE = 'underline'

LINE_STYLES = [CENTER, LEFT, RIGHT, RESET]

def apply_styles(text, styles, reset=True):
    if styles is None:
        return text + ('`f' if reset else '') + ('`b' if reset else '')
    
    line_styles = [s for s in styles if s in LINE_STYLES]
    inline_styles = [s for s in styles if s not in LINE_STYLES]
    line_prefix = ''.join('`' + s for s in line_styles)
    result = text
    for style in inline_styles:
        if style.startswith('F'):
            result = '`' + style + result + ('`f' if reset else '') 
        elif style.startswith('B'):
            result = '`' + style + result + ('`b' if reset else '')
        elif style == BOLD:
            result = '`!' + result + '`!'
        elif style == ITALIC:
            result = '`*' + result + '`*'
        elif style == UNDERLINE:
            result = '`_' + result + '`_'
    return line_prefix + result

class Element:
    def __init__(self, subnodes=None, style=None):
        self.subnodes = subnodes or []
        self.style = style or []

    def render(self, indent=0, parent_style=[]):
        raise NotImplementedError

class Micron(Element):
    def render(self, indent=0):
        return '\n'.join(subnode.render(indent) for subnode in self.subnodes)

    def build(self):
        return (self.render() + "\n# Made using LXMKit").encode("utf-8")

class Header(Element):
    def __init__(self, content, subnodes=None, style=None):
        super().__init__(subnodes, style)
        self.content = content

    def render(self, indent=0, parent_style=[]):
        level = indent + 1
        heading = '>' * level + ' ' + apply_styles(self.content, self.style, False)

        parent_style = parent_style or self.style
        
        subcontent = '\n'.join(subnode.render(level, parent_style) for subnode in self.subnodes)
        return heading + '\n' + subcontent

class Div(Element):
    def __init__(self, subnodes=None, style=None):
        super().__init__(subnodes, style)

    def render(self, indent=0, parent_style=[]):
        level = indent
        parent_style = parent_style or self.style

        content = ''
        for subnode in self.subnodes:
            if isinstance(subnode, Hr) or isinstance(subnode, Header):
                content += "\n" + subnode.render(level, parent_style)
            else:
                content += "\n" + "  " * indent + subnode.render(level, parent_style)

        content = apply_styles(content, self.style, False)

        if not self.style == parent_style:
            content = content + apply_styles("", parent_style, False)

        return content
    
class Paragraph(Element):
    def __init__(self, content, style=None):
        super().__init__(style=style)
        self.content = content

    def render(self, indent=0, parent_style=[]):
        return apply_styles(self.content, self.style)

class Span(Element):
    def __init__(self, subnodes=[], style=None):
        super().__init__(subnodes=subnodes, style=style)

    def render(self, indent=0, parent_style=[]):
        parent_style = parent_style or self.style

        parent_style = [i for i in parent_style if i not in LINE_STYLES] + [i for i in self.style if i in LINE_STYLES]
        
        return ''.join(subnode.render(indent, parent_style) for subnode in self.subnodes)

class Input(Element):
    def __init__(self, name, default="", size=None, masked=False, style=None):
        super().__init__(style=style)
        self.name = name
        self.default = default
        self.size = size
        self.masked = masked

    def render(self, indent=0, parent_style=[]):
        prefix = '`<'
        size_part = f"{self.size}|" if self.size else ""
        masked_part = f"!" if self.masked else ""
        
        content = apply_styles(f'{prefix}{masked_part}{size_part}{self.name}`{self.default}>', self.style, True)

        if not self.style == parent_style:
            content = content + apply_styles("", parent_style, False)
    
        return content

class Checkbox(Element):
    def __init__(self, name="checkbox", value="1", checked=False):
        super().__init__()
        self.name = name
        self.value = value
        self.checked = checked

    def render(self, indent=0, parent_style=[]):
        if self.checked:
            return f'`< ?|{self.name}|{self.value}|*`>'
        return f'`< ?|{self.name}|{self.value}`>'

class Radio(Element):
    def __init__(self, name, value, checked=False, style=None):
        super().__init__(style=style)
        self.name = name
        self.value = value
        self.checked = checked

    def render(self, indent=0, parent_style=[]):
        check_part = '|*' if self.checked else ''
        
        content = f'`<^|{self.name}|{self.value}{check_part}`>'
        
        content = apply_styles(content, self.style, True)
    
        if not self.style == parent_style:
            content = content + apply_styles("", parent_style, False)
        
        return content

class Anchor(Element):
    def __init__(self, content, href, style=None):
        super().__init__(style=style)
        self.content = content
        self.href = href

    def render(self, indent=0, parent_style=[]):
        content =  apply_styles(f'`[{self.content}`{self.href}]', self.style)
        if not self.style == parent_style:
            content = content + apply_styles("", parent_style, False)
        
        return content
    
class Br(Element):
    def __init__(self, style=None):
        super().__init__(style=style)

    def render(self, indent=0, parent_style=[]):
        return ""
    
class Hr(Element):
    def __init__(self, style=None, type=""):
        super().__init__(style=style)
        self.type = type

    def render(self, indent=0, parent_style=[]):
        return apply_styles('-' + self.type, self.style, reset=False)

if __name__ == "__main__":
    canvas = Micron([
        Header(
            "Login Form Example",
            [
                Div([
                    Br(),
                    Span([Paragraph("Username: "), Input("name", "Anonymous", 16, style=[BACKGROUND_DARK_GREY])]),
                    Span([Paragraph("Password: "), Input("pass", "password123", 16, style=[BACKGROUND_DARK_GREY])]),
                    Br(),
                    Anchor("   Submit   ", href=None, style=[BACKGROUND_DARK_GREY]),
                    Br(),
                ], style=[BACKGROUND_DARKER_GREY, CENTER])
            ]
        )
    ])
    
    print(canvas.render())