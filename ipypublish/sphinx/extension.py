import os
from docutils.parsers import rst

from ipypublish import __version__
from ipypublish.sphinx.directives import (NbInfo, NbInput, NbOutput, NbWarning,
                                          AdmonitionNode, CodeAreaNode,
                                          FancyOutputNode)
from ipypublish.sphinx.docutils_transforms import (
    CreateDomainObjectLabels, CreateSectionLabels, RewriteLocalLinks
)
from ipypublish.sphinx.utils import import_sphinx

try:
    from sphinx.application import Sphinx  # noqa: F401
except ImportError:
    pass


def setup(app):
    # type: (Sphinx) -> dict
    """Initialize Sphinx extension.

    TODO latex output 
    (but not really interested in this as it would be duplication of effort)
    """

    sphinx = import_sphinx()

    # variables for cell prompts
    app.add_config_value('nbsphinx_show_prompts', False, rebuild='env')
    app.add_config_value('nbsphinx_input_prompt', '[%s]:', rebuild='env')
    app.add_config_value('nbsphinx_output_prompt', '[%s]:', rebuild='env')

    # add the main directives
    app.add_directive('nbinput', NbInput)
    app.add_directive('nboutput', NbOutput)
    app.add_directive('nbinfo', NbInfo)
    app.add_directive('nbwarning', NbWarning)

    # add docutils nodes and visit/depart wraps
    app.add_node(CodeAreaNode,
                 html=(
                     lambda self, node: None,
                     depart_codearea_html
                 ),
                 #  latex=(
                 #      lambda self, node: self.pushbody([]),  # used in depart
                 #      lambda self, node: None,
                 #  )
                 )
    app.add_node(FancyOutputNode,
                 html=(
                     lambda self, node: None,
                     lambda self, node: None,
                 ),
                 #  latex=(
                 #      lambda self, node: None,
                 #      lambda self, node: None,
                 #  )
                 )
    app.add_node(AdmonitionNode,
                 html=(
                     visit_admonition_html,
                     lambda self, node:
                     self.body.append('</div>\n')
                 ),
                 #  latex=(
                 #      lambda self, node:
                 #      self.body.append(
                 #          '\n\\begin{{sphinxadmonition}}{{{class}}}'
                 #          '{{}}\\unskip'.format(node['classes'][1])),
                 #      lambda self, node:
                 #      self.body.append('\\end{sphinxadmonition}\n')
                 #  )
                 )

    # setup html style
    app.add_config_value('nbsphinx_responsive_width', '540px', rebuild='html')
    app.add_config_value('nbsphinx_prompt_width', None, rebuild='html')
    app.add_config_value('nbsphinx_custom_formats', {}, rebuild='env')
    app.connect('builder-inited', builder_inited)
    app.connect('html-page-context', html_add_css)

    # add transformations
    app.add_transform(CreateSectionLabels)
    app.add_transform(CreateDomainObjectLabels)
    app.add_transform(RewriteLocalLinks)

    # Work-around until https://github.com/sphinx-doc/sphinx/pull/5504 is done:
    mathjax_config = app.config._raw_config.setdefault('mathjax_config', {})
    mathjax_config.setdefault(
        'tex2jax',
        {
            'inlineMath': [['$', '$'], ['\\(', '\\)']],
            'processEscapes': True,
            'ignoreClass': 'document',
            'processClass': 'math|output_area',
        }
    )

    # Make docutils' "code" directive (generated by markdown2rst/pandoc)
    # behave like Sphinx's "code-block",
    # see https://github.com/sphinx-doc/sphinx/issues/2155:
    rst.directives.register_directive('code', sphinx.directives.code.CodeBlock)

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        'env_version': 1,
    }


def visit_admonition_html(self, node):
    self.body.append(self.starttag(node, 'div'))
    if len(node.children) >= 2:
        node[0]['classes'].append('admonition-title')
        html_theme = self.settings.env.config.html_theme
        if html_theme in ('sphinx_rtd_theme', 'julia'):
            node.children[0]['classes'].extend(['fa', 'fa-exclamation-circle'])


def depart_codearea_html(self, node):
    """Add empty lines before and after the code."""
    text = self.body[-1]
    text = text.replace('<pre>',
                        '<pre>\n' + '\n' * node.get('empty-lines-before', 0))
    text = text.replace('</pre>',
                        '\n' * node.get('empty-lines-after', 0) + '</pre>')
    self.body[-1] = text


def read_css(name):
    folder = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                          "css")
    with open(os.path.join(folder, name + ".css")) as fobj:
        content = fobj.read()

    return content


def builder_inited(app):
    # Set default value for CSS prompt width
    if app.config.nbsphinx_prompt_width is None:
        app.config.nbsphinx_prompt_width = {
            'agogo': '4ex',
            'alabaster': '5ex',
            'better': '5ex',
            'classic': '4ex',
            'cloud': '5ex',
            'dotted': '5ex',
            'haiku': '4ex',
            'julia': '5ex',
            'nature': '5ex',
            'pyramid': '5ex',
            'redcloud': '5ex',
            'sphinx_py3doc_enhanced_theme': '6ex',
            'sphinx_rtd_theme': '5ex',
            'traditional': '4ex',
        }.get(app.config.html_theme, '7ex')

    for suffix in app.config.nbsphinx_custom_formats:
        app.add_source_suffix(suffix, 'jupyter_notebook')


def html_add_css(app, pagename, templatename, context, doctree):
    """Add CSS string to HTML pages that contain code cells."""
    style = ''
    if doctree and doctree.get('nbsphinx_include_css'):
        style += read_css('nb_cells') % app.config
    if doctree and app.config.html_theme in ('sphinx_rtd_theme', 'julia'):
        style += read_css('sphinx_rtd_theme')
    if doctree and app.config.html_theme in ('cloud', 'redcloud'):
        style += read_css('cloud_theme')
    if style:
        context['body'] = '\n<style>' + style + '</style>\n' + context['body']