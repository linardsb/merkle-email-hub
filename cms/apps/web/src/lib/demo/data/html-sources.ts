/**
 * Realistic Maizzle-compiled email HTML templates.
 * Each composes header + hero/content + CTA + footer components
 * into complete email documents with proper DOCTYPE, VML namespaces,
 * color-scheme meta, and dark mode CSS.
 */

const EMAIL_WRAPPER_START = `<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{subject}}</title>
  <!--[if mso]>
  <noscript><xml>
    <o:OfficeDocumentSettings>
      <o:PixelsPerInch>96</o:PixelsPerInch>
    </o:OfficeDocumentSettings>
  </xml></noscript>
  <![endif]-->
  <style>
    body { margin: 0; padding: 0; width: 100%; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    table { border-collapse: collapse; mso-table-lspace: 0; mso-table-rspace: 0; }
    img { border: 0; display: block; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic; }
    @media (prefers-color-scheme: dark) {
      body { background-color: #1a1a2e !important; }
      .email-body { background-color: #1a1a2e !important; }
      .header-bg { background-color: #1a1a2e !important; }
      .footer-bg { background-color: #1a1a2e !important; }
      .content-bg { background-color: #2d2d44 !important; }
      .hero-overlay { background-color: rgba(0,0,0,0.7) !important; }
      .dark-text { color: #e0e0e0 !important; }
      .dark-muted { color: #b0b0b0 !important; }
      .dark-link { color: #8ecae6 !important; }
    }
    [data-ogsc] .header-bg { background-color: #1a1a2e !important; }
    [data-ogsc] .footer-bg { background-color: #1a1a2e !important; }
    [data-ogsc] .content-bg { background-color: #2d2d44 !important; }
    [data-ogsc] .dark-text { color: #e0e0e0 !important; }
    [data-ogsc] .dark-muted { color: #b0b0b0 !important; }
  </style>
</head>
<body class="email-body" style="margin: 0; padding: 0; background-color: #f5f5f5;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td align="center" style="padding: 24px 16px;">
        <!--[if mso]><table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px;">`;

const EMAIL_WRAPPER_END = `        </table>
        <!--[if mso]></td></tr></table><![endif]-->
      </td>
    </tr>
  </table>
</body>
</html>`;

function wrapEmail(subject: string, body: string): string {
  return EMAIL_WRAPPER_START.replace("{{subject}}", subject) + "\n" + body + "\n" + EMAIL_WRAPPER_END;
}

// --- Inline SVG placeholder images (render in sandboxed iframes without external requests) ---
function _img(w: number, h: number, bg: string, label: string, fg = "#fff"): string {
  const fs = Math.max(11, Math.min(28, Math.floor(Math.min(w, h) / 4)));
  return `data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect fill="${bg}" width="${w}" height="${h}" rx="4"/><text x="${w / 2}" y="${h / 2 + Math.floor(fs / 3)}" fill="${fg}" font-family="Arial,sans-serif" font-size="${fs}" font-weight="bold" text-anchor="middle">${label}</text></svg>`
  )}`;
}

const IMG_APEX = _img(150, 40, "#E4002B", "APEX");
const IMG_SPRING = _img(600, 300, "#4CAF50", "Spring Collection");
const IMG_BLAZER = _img(280, 200, "#C8E6C9", "Linen Blazer", "#333");
const IMG_DRESS = _img(280, 200, "#FFE0B2", "Cotton Dress", "#333");
const IMG_VALENTINE = _img(600, 300, "#FFCDD2", "Valentine\u2019s", "#C62828");
const IMG_UNDER25 = _img(180, 180, "#FFEBEE", "Under \u00A325", "#C62828");
const IMG_UNDER50 = _img(180, 180, "#FFEBEE", "Under \u00A350", "#C62828");
const IMG_LUXURY = _img(180, 180, "#FFEBEE", "Luxury", "#C62828");
const IMG_FOR_HER = _img(270, 200, "#FCE4EC", "For Her", "#333");
const IMG_FOR_HIM = _img(270, 200, "#E8EAF6", "For Him", "#333");
const IMG_BEST1 = _img(270, 200, "#C8E6C9", "Essential Tee", "#333");
const IMG_BEST2 = _img(270, 200, "#BBDEFB", "Canvas Bag", "#333");
const IMG_SUMMER = _img(600, 350, "#81D4FA", "Summer 2026");

// ── Spring Sale Hero (Project 1, Template 1) ──
export const SPRING_SALE_HERO_HTML = wrapEmail(
  "Spring Into Savings — Up to 40% Off",
  `<!-- Header -->
          <tr>
            <td>
              <table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
                <tr>
                  <td style="padding: 20px 24px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="width: 150px;"><img src="${IMG_APEX}" alt="Apex Retail" width="150" height="40" style="display:block;border:0;" /></td>
                        <td style="text-align:right;vertical-align:middle;">
                          <a href="https://example.com" class="dark-link" style="color:#333;text-decoration:none;font-family:Arial,sans-serif;font-size:14px;padding:0 8px;">Shop</a>
                          <a href="https://example.com/sale" class="dark-link" style="color:#333;text-decoration:none;font-family:Arial,sans-serif;font-size:14px;padding:0 8px;">Sale</a>
                          <a href="https://example.com/new" class="dark-link" style="color:#333;text-decoration:none;font-family:Arial,sans-serif;font-size:14px;padding:0 8px;">New In</a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Hero -->
          <tr>
            <td>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-image:url('${IMG_SPRING}');background-size:cover;background-position:center;">
                <tr>
                  <td class="hero-overlay" style="padding:48px 24px;text-align:center;background-color:rgba(0,0,0,0.4);">
                    <h1 class="dark-text" style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:32px;font-weight:bold;color:#ffffff;line-height:1.2;">
                      Spring Into Savings
                    </h1>
                    <p class="dark-muted" style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:16px;color:#e0e0e0;line-height:1.5;">
                      Up to 40% off across our entire spring collection. Fresh styles, vibrant colours, unbeatable prices.
                    </p>
                    <a href="https://example.com/spring-sale" style="display:inline-block;padding:14px 36px;background-color:#E4002B;color:#ffffff;text-decoration:none;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;border-radius:4px;">Shop the Sale</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Products -->
          <tr>
            <td>
              <table role="presentation" class="content-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;">
                <tr>
                  <td style="padding:32px 24px;">
                    <h2 class="dark-text" style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:24px;color:#333;text-align:center;">Top Picks This Week</h2>
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td width="50%" style="padding:8px;vertical-align:top;">
                          <img src="${IMG_BLAZER}" alt="Spring Linen Blazer" width="280" style="display:block;width:100%;height:auto;border:0;border-radius:4px;" />
                          <p class="dark-text" style="margin:8px 0 4px;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#333;">Spring Linen Blazer</p>
                          <p style="margin:0;font-family:Arial,sans-serif;font-size:14px;color:#E4002B;font-weight:bold;">&pound;89.00 <span style="color:#999;text-decoration:line-through;font-weight:normal;">&pound;149.00</span></p>
                        </td>
                        <td width="50%" style="padding:8px;vertical-align:top;">
                          <img src="${IMG_DRESS}" alt="Floral Cotton Dress" width="280" style="display:block;width:100%;height:auto;border:0;border-radius:4px;" />
                          <p class="dark-text" style="margin:8px 0 4px;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#333;">Floral Cotton Dress</p>
                          <p style="margin:0;font-family:Arial,sans-serif;font-size:14px;color:#E4002B;font-weight:bold;">&pound;59.00 <span style="color:#999;text-decoration:line-through;font-weight:normal;">&pound;95.00</span></p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- CTA -->
          <tr>
            <td style="padding:24px 0;text-align:center;background-color:#ffffff;">
              <!--[if mso]>
              <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="https://example.com/spring-sale" style="height:48px;v-text-anchor:middle;width:220px;" arcsize="10%" fillcolor="#E4002B">
                <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">View All Deals</center>
              </v:roundrect>
              <![endif]-->
              <!--[if !mso]><!-->
              <a href="https://example.com/spring-sale" style="display:inline-block;padding:14px 40px;background-color:#E4002B;color:#ffffff;text-decoration:none;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;border-radius:4px;">View All Deals</a>
              <!--<![endif]-->
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td>
              <table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
                <tr>
                  <td style="padding:32px 24px;text-align:center;">
                    <p class="dark-muted" style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:12px;color:#666;line-height:1.5;">&copy; 2026 Apex Retail Group. All rights reserved.</p>
                    <p class="dark-muted" style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:12px;color:#666;line-height:1.5;">123 High Street, London, EC1A 1BB</p>
                    <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;">
                      <a href="#" class="dark-link" style="color:#0066cc;text-decoration:underline;">Unsubscribe</a> &nbsp;|&nbsp;
                      <a href="#" class="dark-link" style="color:#0066cc;text-decoration:underline;">Manage Preferences</a> &nbsp;|&nbsp;
                      <a href="#" class="dark-link" style="color:#0066cc;text-decoration:underline;">Privacy Policy</a>
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>`
);

// ── Spring Sale Reminder (Project 1, Template 2) ──
export const SPRING_SALE_REMINDER_HTML = wrapEmail(
  "Don't Miss Out — Spring Sale Ends Soon",
  `          <tr><td>
              <table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;">
                <tr><td style="padding:20px 24px;">
                  <img src="${IMG_APEX}" alt="Apex Retail" width="150" height="40" style="display:block;border:0;" />
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="content-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;">
                <tr><td style="padding:40px 24px;text-align:center;">
                  <h1 class="dark-text" style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:28px;font-weight:bold;color:#333;">Hurry — Sale Ends This Weekend!</h1>
                  <p class="dark-muted" style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:16px;color:#555;line-height:1.6;">
                    Your favourite spring styles are selling fast. Don't miss your chance to save up to 40% before it's too late.
                  </p>
                  <a href="https://example.com/spring-sale" style="display:inline-block;padding:14px 36px;background-color:#E4002B;color:#fff;text-decoration:none;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;border-radius:4px;">Shop Now</a>
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
                <tr><td style="padding:32px 24px;text-align:center;">
                  <p class="dark-muted" style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:12px;color:#666;">&copy; 2026 Apex Retail Group. All rights reserved.</p>
                  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;">
                    <a href="#" class="dark-link" style="color:#0066cc;text-decoration:underline;">Unsubscribe</a> &nbsp;|&nbsp;
                    <a href="#" class="dark-link" style="color:#0066cc;text-decoration:underline;">Manage Preferences</a>
                  </p>
                </td></tr>
              </table>
          </td></tr>`
);

// ── Spring Sale Last Chance (Project 1, Template 3) ──
export const SPRING_SALE_LAST_CHANCE_HTML = wrapEmail(
  "FINAL HOURS — Spring Sale Ends Tonight",
  `          <tr><td>
              <table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;">
                <tr><td style="padding:20px 24px;">
                  <img src="${IMG_APEX}" alt="Apex Retail" width="150" height="40" style="display:block;border:0;" />
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#E4002B;">
                <tr><td style="padding:40px 24px;text-align:center;">
                  <h1 style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:32px;font-weight:bold;color:#fff;letter-spacing:2px;">FINAL HOURS</h1>
                  <p style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:18px;color:#ffe0e0;line-height:1.5;">
                    The Spring Sale ends at midnight. This is your last chance to save up to 40%.
                  </p>
                  <a href="https://example.com/spring-sale" style="display:inline-block;padding:14px 36px;background-color:#fff;color:#E4002B;text-decoration:none;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;border-radius:4px;">Shop Before Midnight</a>
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
                <tr><td style="padding:32px 24px;text-align:center;">
                  <p class="dark-muted" style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:12px;color:#666;">&copy; 2026 Apex Retail Group.</p>
                  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;"><a href="#" style="color:#0066cc;text-decoration:underline;">Unsubscribe</a></p>
                </td></tr>
              </table>
          </td></tr>`
);

// ── Valentine's Day Promo (Project 2, Template 4) ──
export const VALENTINES_PROMO_HTML = wrapEmail(
  "Fall in Love With These Deals",
  `          <tr><td>
              <table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;">
                <tr><td style="padding:20px 24px;">
                  <img src="${IMG_APEX}" alt="Apex Retail" width="150" height="40" style="display:block;border:0;" />
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-image:url('${IMG_VALENTINE}');background-size:cover;background-position:center;">
                <tr><td style="padding:48px 24px;text-align:center;background-color:rgba(228,0,43,0.15);">
                  <h1 class="dark-text" style="margin:0 0 16px;font-family:Georgia,serif;font-size:36px;font-weight:bold;color:#E4002B;line-height:1.2;">
                    Fall in Love With These Deals
                  </h1>
                  <p class="dark-muted" style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:16px;color:#555;line-height:1.5;">
                    Discover the perfect gift for your Valentine. Curated collections with free gift wrapping on all orders.
                  </p>
                  <a href="https://example.com/valentines" style="display:inline-block;padding:14px 36px;background-color:#E4002B;color:#fff;text-decoration:none;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;border-radius:4px;">Shop Valentine's Gifts</a>
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="content-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
                <tr><td style="padding:32px 24px;">
                  <h2 class="dark-text" style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:22px;color:#333;text-align:center;">Gift Ideas by Budget</h2>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                      <td width="33%" style="padding:8px;text-align:center;vertical-align:top;">
                        <img src="${IMG_UNDER25}" alt="Under 25 pounds" width="180" style="display:block;width:100%;height:auto;border:0;border-radius:50%;" />
                        <p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#E4002B;">Under &pound;25</p>
                      </td>
                      <td width="33%" style="padding:8px;text-align:center;vertical-align:top;">
                        <img src="${IMG_UNDER50}" alt="Under 50 pounds" width="180" style="display:block;width:100%;height:auto;border:0;border-radius:50%;" />
                        <p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#E4002B;">Under &pound;50</p>
                      </td>
                      <td width="33%" style="padding:8px;text-align:center;vertical-align:top;">
                        <img src="${IMG_LUXURY}" alt="Luxury gifts" width="180" style="display:block;width:100%;height:auto;border:0;border-radius:50%;" />
                        <p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#E4002B;">Luxury</p>
                      </td>
                    </tr>
                  </table>
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
                <tr><td style="padding:32px 24px;text-align:center;">
                  <p class="dark-muted" style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:12px;color:#666;">&copy; 2026 Apex Retail Group.</p>
                  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;">
                    <a href="#" style="color:#0066cc;text-decoration:underline;">Unsubscribe</a> &nbsp;|&nbsp;
                    <a href="#" style="color:#0066cc;text-decoration:underline;">Privacy Policy</a>
                  </p>
                </td></tr>
              </table>
          </td></tr>`
);

// ── Valentine's Gift Guide (Project 2, Template 5) ──
export const VALENTINES_GIFT_GUIDE_HTML = wrapEmail(
  "The Ultimate Valentine's Gift Guide",
  `          <tr><td>
              <table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
                <tr><td style="padding:20px 24px;">
                  <img src="${IMG_APEX}" alt="Apex Retail" width="150" height="40" style="display:block;border:0;" />
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="content-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
                <tr><td style="padding:32px 24px;text-align:center;">
                  <h1 class="dark-text" style="margin:0 0 16px;font-family:Georgia,serif;font-size:30px;color:#333;">The Ultimate Gift Guide</h1>
                  <p class="dark-muted" style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:16px;color:#555;line-height:1.6;">
                    Not sure what to get? We've curated the best gifts for every special person in your life.
                  </p>
                </td></tr>
                <tr><td style="padding:0 24px 32px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                      <td width="50%" style="padding:8px;vertical-align:top;">
                        <img src="${IMG_FOR_HER}" alt="Gifts for Her" width="270" style="display:block;width:100%;height:auto;border:0;border-radius:8px;" />
                        <h3 class="dark-text" style="margin:12px 0 4px;font-family:Arial,sans-serif;font-size:16px;color:#333;">For Her</h3>
                        <p class="dark-muted" style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:13px;color:#666;">Jewellery, fragrances, and more</p>
                        <a href="#" style="font-family:Arial,sans-serif;font-size:13px;color:#E4002B;font-weight:bold;text-decoration:none;">Shop Now &rarr;</a>
                      </td>
                      <td width="50%" style="padding:8px;vertical-align:top;">
                        <img src="${IMG_FOR_HIM}" alt="Gifts for Him" width="270" style="display:block;width:100%;height:auto;border:0;border-radius:8px;" />
                        <h3 class="dark-text" style="margin:12px 0 4px;font-family:Arial,sans-serif;font-size:16px;color:#333;">For Him</h3>
                        <p class="dark-muted" style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:13px;color:#666;">Watches, tech, and grooming</p>
                        <a href="#" style="font-family:Arial,sans-serif;font-size:13px;color:#E4002B;font-weight:bold;text-decoration:none;">Shop Now &rarr;</a>
                      </td>
                    </tr>
                  </table>
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
                <tr><td style="padding:32px 24px;text-align:center;">
                  <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:12px;color:#666;">&copy; 2026 Apex Retail Group.</p>
                  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;"><a href="#" style="color:#0066cc;text-decoration:underline;">Unsubscribe</a></p>
                </td></tr>
              </table>
          </td></tr>`
);

// ── Welcome Email #1 (Project 3, Template 6) ──
export const WELCOME_EMAIL_1_HTML = wrapEmail(
  "Welcome to Apex Retail — Here's 15% Off",
  `          <tr><td>
              <table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
                <tr><td style="padding:20px 24px;text-align:center;">
                  <img src="${IMG_APEX}" alt="Apex Retail" width="150" height="40" style="display:block;margin:0 auto;border:0;" />
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="content-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
                <tr><td style="padding:40px 24px;text-align:center;">
                  <h1 class="dark-text" style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:28px;color:#333;">Welcome to the Family!</h1>
                  <p class="dark-muted" style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:16px;color:#555;line-height:1.6;">
                    We're thrilled to have you. As a welcome gift, here's <strong>15% off</strong> your first order. Use code <strong style="color:#E4002B;">WELCOME15</strong> at checkout.
                  </p>
                  <a href="https://example.com/shop" style="display:inline-block;padding:14px 36px;background-color:#E4002B;color:#fff;text-decoration:none;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;border-radius:4px;">Start Shopping</a>
                  <p class="dark-muted" style="margin:16px 0 0;font-family:Arial,sans-serif;font-size:13px;color:#999;">Code valid for 30 days. One use per customer.</p>
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
                <tr><td style="padding:32px 24px;text-align:center;">
                  <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:12px;color:#666;">&copy; 2026 Apex Retail Group.</p>
                  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;"><a href="#" style="color:#0066cc;text-decoration:underline;">Unsubscribe</a></p>
                </td></tr>
              </table>
          </td></tr>`
);

// ── Welcome Email #2 (Project 3, Template 7) ──
export const WELCOME_EMAIL_2_HTML = wrapEmail(
  "Discover Our Bestsellers — Curated for You",
  `          <tr><td>
              <table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
                <tr><td style="padding:20px 24px;text-align:center;">
                  <img src="${IMG_APEX}" alt="Apex Retail" width="150" height="40" style="display:block;margin:0 auto;border:0;" />
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="content-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
                <tr><td style="padding:32px 24px;">
                  <h1 class="dark-text" style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:26px;color:#333;text-align:center;">Our Bestsellers, Just for You</h1>
                  <p class="dark-muted" style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:16px;color:#555;line-height:1.6;text-align:center;">
                    Here are some of our most-loved products to get you started.
                  </p>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                      <td width="50%" style="padding:8px;vertical-align:top;">
                        <img src="${IMG_BEST1}" alt="Product 1" width="270" style="display:block;width:100%;height:auto;border:0;border-radius:4px;" />
                        <p class="dark-text" style="margin:8px 0 4px;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#333;">Essential Cotton Tee</p>
                        <p style="margin:0;font-family:Arial,sans-serif;font-size:14px;color:#E4002B;font-weight:bold;">&pound;29.00</p>
                      </td>
                      <td width="50%" style="padding:8px;vertical-align:top;">
                        <img src="${IMG_BEST2}" alt="Product 2" width="270" style="display:block;width:100%;height:auto;border:0;border-radius:4px;" />
                        <p class="dark-text" style="margin:8px 0 4px;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#333;">Weekend Canvas Bag</p>
                        <p style="margin:0;font-family:Arial,sans-serif;font-size:14px;color:#E4002B;font-weight:bold;">&pound;45.00</p>
                      </td>
                    </tr>
                  </table>
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
                <tr><td style="padding:32px 24px;text-align:center;">
                  <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:12px;color:#666;">&copy; 2026 Apex Retail Group.</p>
                  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;"><a href="#" style="color:#0066cc;text-decoration:underline;">Unsubscribe</a></p>
                </td></tr>
              </table>
          </td></tr>`
);

// ── Summer Collection Preview (Project 4, Template 8) ──
export const SUMMER_PREVIEW_HTML = wrapEmail(
  "Coming Soon — Summer Collection 2026",
  `          <tr><td>
              <table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fff;">
                <tr><td style="padding:20px 24px;">
                  <img src="${IMG_APEX}" alt="Apex Retail" width="150" height="40" style="display:block;border:0;" />
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-image:url('${IMG_SUMMER}');background-size:cover;background-position:center;">
                <tr><td style="padding:60px 24px;text-align:center;background-color:rgba(0,0,0,0.3);">
                  <p style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:14px;color:#FFD700;font-weight:bold;letter-spacing:3px;text-transform:uppercase;">Coming Soon</p>
                  <h1 style="margin:0 0 16px;font-family:Georgia,serif;font-size:36px;font-weight:bold;color:#fff;line-height:1.2;">Summer Collection 2026</h1>
                  <p style="margin:0 0 24px;font-family:Arial,sans-serif;font-size:16px;color:#e0e0e0;line-height:1.5;">
                    Sun-ready styles dropping April 1st. Be the first to see what's new.
                  </p>
                  <a href="https://example.com/summer" style="display:inline-block;padding:14px 36px;background-color:#fff;color:#333;text-decoration:none;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;border-radius:4px;">Get Early Access</a>
                </td></tr>
              </table>
          </td></tr>
          <tr><td>
              <table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
                <tr><td style="padding:32px 24px;text-align:center;">
                  <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:12px;color:#666;">&copy; 2026 Apex Retail Group.</p>
                  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;"><a href="#" style="color:#0066cc;text-decoration:underline;">Unsubscribe</a></p>
                </td></tr>
              </table>
          </td></tr>`
);
