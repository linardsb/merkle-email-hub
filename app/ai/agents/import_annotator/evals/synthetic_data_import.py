"""Synthetic test cases for import annotator evaluation."""

IMPORT_ANNOTATOR_TEST_CASES: list[dict] = [  # type: ignore[type-arg]
    {
        "id": "import-001",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "simple",
            "esp_syntax": "none",
            "column_layout": "single",
        },
        "brief": (
            '<html><body><table width="600" align="center"><tbody>'
            '<tr><td><img src="logo.png" alt="Logo" width="200"></td></tr>'
            "<tr><td><h1>Welcome</h1><p>Hero section with large image.</p></td></tr>"
            "<tr><td><p>Main content paragraph here.</p></td></tr>"
            '<tr><td><a href="https://example.com">Click Here</a></td></tr>'
            '<tr><td><p style="font-size:12px;">Unsubscribe | Privacy Policy</p></td></tr>'
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Identify header, hero, content, CTA, footer sections in nested tables",
            "Correct section boundary at outermost content table rows",
        ],
    },
    {
        "id": "import-002",
        "dimensions": {
            "layout_type": "div_based",
            "complexity": "simple",
            "esp_syntax": "none",
            "column_layout": "single",
        },
        "brief": (
            '<html><body><div class="email-body">'
            '<div class="header"><img src="logo.png" alt="Logo"></div>'
            '<div class="hero"><h1>Big Headline</h1><img src="hero.jpg"></div>'
            '<div class="content"><p>Some body text here.</p></div>'
            '<div class="cta"><a href="https://example.com" class="button">Shop Now</a></div>'
            '<div class="footer"><p>© 2026 Company</p></div>'
            "</div></body></html>"
        ),
        "expected_challenges": [
            "Identify sections from div-based semantic structure",
            "Map class names to component types",
        ],
    },
    {
        "id": "import-003",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "medium",
            "esp_syntax": "none",
            "column_layout": "two_column",
        },
        "brief": (
            '<html><body><table width="600" align="center"><tbody>'
            '<tr><td colspan="2"><img src="logo.png" alt="Logo"></td></tr>'
            '<tr><td width="50%"><img src="product1.jpg"></td>'
            '<td width="50%"><img src="product2.jpg"></td></tr>'
            '<tr><td colspan="2"><p>Footer text</p></td></tr>'
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Detect 2-column layout in second row",
            "Annotate parent row with columns layout, not individual cells",
        ],
    },
    {
        "id": "import-004",
        "dimensions": {
            "layout_type": "div_based",
            "complexity": "medium",
            "esp_syntax": "none",
            "column_layout": "three_column",
        },
        "brief": (
            '<html><body><div class="wrapper">'
            '<div class="header"><img src="logo.png"></div>'
            '<div class="columns-row">'
            '<div style="display:inline-block;width:33%;vertical-align:top;">Col 1</div>'
            '<div style="display:inline-block;width:33%;vertical-align:top;">Col 2</div>'
            '<div style="display:inline-block;width:33%;vertical-align:top;">Col 3</div>'
            "</div>"
            '<div class="footer"><p>Footer</p></div>'
            "</div></body></html>"
        ),
        "expected_challenges": [
            "Detect 3-column inline-block layout",
            "Annotate parent div as columns section, not individual column divs",
        ],
    },
    {
        "id": "import-005",
        "dimensions": {
            "layout_type": "div_based",
            "complexity": "complex",
            "esp_syntax": "none",
            "column_layout": "fab_four",
        },
        "brief": (
            '<html><body><div class="email-container">'
            '<div class="header"><img src="logo.png"></div>'
            '<div class="responsive-row">'
            '<div style="display:inline-block;min-width:200px;max-width:50%;'
            'width:calc(50% - 20px);">Column A</div>'
            '<div style="display:inline-block;min-width:200px;max-width:50%;'
            'width:calc(50% - 20px);">Column B</div>'
            "</div>"
            '<div class="footer"><p>Footer</p></div>'
            "</div></body></html>"
        ),
        "expected_challenges": [
            "Detect Fab Four calc-based responsive columns",
            "Annotate parent as columns section",
        ],
    },
    {
        "id": "import-006",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "complex",
            "esp_syntax": "none",
            "column_layout": "single",
        },
        "brief": (
            "<html><body>"
            '<table width="100%"><tr><td align="center">'
            '<table width="600"><tr><td>'
            '<table width="100%"><tr><td>'
            '<table width="100%"><tr><td>'
            '<table width="100%"><tbody>'
            '<tr><td><img src="logo.png"></td></tr>'
            "<tr><td><h1>Deep Nested</h1></td></tr>"
            "<tr><td><p>Content</p></td></tr>"
            "<tr><td><p>Footer</p></td></tr>"
            "</tbody></table>"
            "</td></tr></table>"
            "</td></tr></table>"
            "</td></tr></table>"
            "</td></tr></table>"
            "</body></html>"
        ),
        "expected_challenges": [
            "Navigate 5 levels of nested tables to find content table",
            "Correctly identify section boundaries at innermost content level",
        ],
    },
    {
        "id": "import-007",
        "dimensions": {
            "layout_type": "hybrid",
            "complexity": "medium",
            "esp_syntax": "none",
            "column_layout": "mixed",
        },
        "brief": (
            '<html><body><table width="600" align="center"><tbody>'
            '<tr><td><div class="header"><img src="logo.png"></div></td></tr>'
            '<tr><td><div class="hero" style="text-align:center;"><h1>Title</h1></div></td></tr>'
            '<tr><td><table width="100%"><tr>'
            '<td width="50%">Left col</td><td width="50%">Right col</td>'
            "</tr></table></td></tr>"
            '<tr><td><div class="footer"><p>Footer</p></div></td></tr>'
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Handle hybrid table + div layout",
            "Detect nested table columns within outer table row",
        ],
    },
    {
        "id": "import-008",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "medium",
            "esp_syntax": "liquid",
            "column_layout": "single",
        },
        "brief": (
            '<html><body><table width="600" align="center"><tbody>'
            '<tr><td><img src="{{ brand.logo_url }}" alt="{{ brand.name }}"></td></tr>'
            "{% if show_hero %}"
            "<tr><td><h1>{{ hero_title }}</h1></td></tr>"
            "{% endif %}"
            "<tr><td><p>{{ content_body }}</p></td></tr>"
            "{% for product in products %}"
            "<tr><td><p>{{ product.name }} - {{ product.price }}</p></td></tr>"
            "{% endfor %}"
            "<tr><td><p>© {{ current_year }} {{ brand.name }}</p></td></tr>"
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Preserve all Liquid tokens unchanged",
            "Handle conditional section wrapping ({% if %} around <tr>)",
            "Handle for-loop sections",
        ],
    },
    {
        "id": "import-009",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "complex",
            "esp_syntax": "ampscript",
            "column_layout": "single",
        },
        "brief": (
            '<html><body><table width="600" align="center"><tbody>'
            '<tr><td><img src="%%=v(@logoUrl)=%%" alt="Logo"></td></tr>'
            "%%[IF @segment == 'vip' THEN]%%"
            "<tr><td><h1>VIP Exclusive</h1></td></tr>"
            "%%[ENDIF]%%"
            "<tr><td><p>%%=v(@firstName)=%%, check out our latest offers.</p></td></tr>"
            "<tr><td>"
            "%%=ContentBlockByKey('footer_block')=%%"
            "</td></tr>"
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Preserve AMPscript tokens unchanged",
            "Handle AMPscript conditionals wrapping table rows",
        ],
    },
    {
        "id": "import-010",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "medium",
            "esp_syntax": "handlebars",
            "column_layout": "single",
        },
        "brief": (
            '<html><body><table width="600" align="center"><tbody>'
            '<tr><td><img src="{{ logoUrl }}" alt="{{{ companyName }}}"></td></tr>'
            "<tr><td><h1>{{ headline }}</h1></td></tr>"
            "{{#if showProducts}}"
            "{{#each products}}"
            "<tr><td><p>{{ this.name }}</p></td></tr>"
            "{{/each}}"
            "{{/if}}"
            "<tr><td><p>{{> footer_partial}}</p></td></tr>"
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Preserve Handlebars tokens including triple-stache {{{ }}}",
            "Handle nested #if and #each blocks",
            "Preserve partial syntax {{> }}",
        ],
    },
    {
        "id": "import-011",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "complex",
            "esp_syntax": "mso",
            "column_layout": "single",
        },
        "brief": (
            "<!DOCTYPE html><html><head>"
            "<!--[if mso]><style>body{font-family:Arial,sans-serif;}</style><![endif]-->"
            "</head><body>"
            '<table width="600" align="center"><tbody>'
            "<tr><td><!--[if gte mso 9]>"
            '<v:rect style="width:600px;height:300px;" stroke="false" fill="true">'
            '<v:fill type="frame" src="hero-bg.jpg"/>'
            '<v:textbox inset="0,0,0,0"><![endif]-->'
            '<div style="background:url(hero-bg.jpg);width:600px;height:300px;">'
            "<h1>Hero with VML</h1></div>"
            "<!--[if gte mso 9]></v:textbox></v:rect><![endif]-->"
            "</td></tr>"
            "<tr><td><p>Content section</p></td></tr>"
            "<tr><td><p>Footer</p></td></tr>"
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Preserve MSO conditionals and VML blocks unchanged",
            "Do not treat MSO comments as section boundaries",
        ],
    },
    {
        "id": "import-012",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "medium",
            "esp_syntax": "none",
            "column_layout": "single",
        },
        "brief": (
            "<html><head><style>"
            ".header { background-color: #333; color: white; }"
            ".content { padding: 20px; }"
            "@media (max-width: 480px) { .responsive { width: 100% !important; } }"
            "</style></head><body>"
            '<table width="600" align="center"><tbody>'
            '<tr class="header"><td><img src="logo.png" alt="Logo"></td></tr>'
            '<tr class="content"><td><p>Content with embedded styles.</p></td></tr>'
            "<tr><td><p>Footer</p></td></tr>"
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Preserve embedded style block unchanged",
            "Handle class-based section identification",
        ],
    },
    {
        "id": "import-013",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "minimal",
            "esp_syntax": "none",
            "column_layout": "single",
        },
        "brief": (
            '<html><body><table width="600" align="center"><tbody>'
            "<tr><td><p>Single section email — no distinct boundaries.</p></td></tr>"
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Handle minimal single-section email",
            "Entire content treated as one Content section",
        ],
    },
    {
        "id": "import-014",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "complex",
            "esp_syntax": "none",
            "column_layout": "mixed",
        },
        "brief": (
            '<html><body><table width="600" align="center"><tbody>'
            '<tr><td><img src="logo.png"><span>|</span><a href="/">Home</a></td></tr>'
            '<tr><td style="height:10px;"></td></tr>'
            '<tr><td><div style="background:url(hero.jpg);height:400px;"><h1>Big Hero</h1></div></td></tr>'
            "<tr><td><p>Intro text paragraph.</p></td></tr>"
            "<tr><td><table><tr>"
            '<td width="33%"><img src="p1.jpg"><p>Product 1</p></td>'
            '<td width="33%"><img src="p2.jpg"><p>Product 2</p></td>'
            '<td width="33%"><img src="p3.jpg"><p>Product 3</p></td>'
            "</tr></table></td></tr>"
            '<tr><td style="height:20px;"></td></tr>'
            "<tr><td><p>Article section text.</p></td></tr>"
            "<tr><td><table><tr>"
            '<td width="50%"><p>Left article</p></td>'
            '<td width="50%"><p>Right article</p></td>'
            "</tr></table></td></tr>"
            '<tr><td style="text-align:center;"><a href="https://example.com" '
            'style="padding:15px 30px;background:#007bff;color:white;">Shop Now</a></td></tr>'
            "<tr><td><hr></td></tr>"
            "<tr><td><p>© 2026 Company | Privacy | Unsubscribe</p></td></tr>"
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Identify 10+ sections including spacers and dividers",
            "Detect 3-column and 2-column nested layouts",
            "Distinguish CTA from content sections",
        ],
    },
    {
        "id": "import-015",
        "dimensions": {
            "layout_type": "table_based",
            "complexity": "simple",
            "esp_syntax": "none",
            "column_layout": "single",
        },
        "brief": (
            '<html><body><table width="600" align="center"><tbody>'
            '<tr data-section-id="existing-1"><td><img src="logo.png"></td></tr>'
            '<tr data-section-id="existing-2"><td><p>Content</p></td></tr>'
            '<tr data-section-id="existing-3"><td><p>Footer</p></td></tr>'
            "</tbody></table></body></html>"
        ),
        "expected_challenges": [
            "Detect already-annotated HTML",
            "Return unchanged with warning — no double annotations",
        ],
    },
]
