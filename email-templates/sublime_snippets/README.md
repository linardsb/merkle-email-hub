Email-Snippets
==============

Internal email snippets seperated by type.

---

# Quick Start Guide

## Layout


**rtab** Basic responsive table

**space** Vertical Spacer

**r2col** Use to create a Left/onto/Right stacking table

**rev2col** Use to create a Right/onto/Left stacking table

**rbase** Use to create a base email template

**3row** Use to create a 3 row table 

**rimg** Create a responsive image

**eimg** Create a non resposnive img

**tv** Center align row and table cell

**tvl** Left aligned row and table cell

**tvr** Right aligned row and table cell



## Text styling


**etxt** Used for setting any html text

**FS** Set font size in a span

**TT** Uppercase in a span

**helv** Helvetic font family



 


Responsive Snippets
------

Responsive snippets are all prefixed with the letter 'r'

**r2col**

Responsive two column stacking section
```html
<table cellpadding="0" cellspacing="0" border="0" width="$1" class="wf">
  <tr class="wr" align="center">
    <td align="center" class="wf wr fl">
      $2
    </td>
    <td align="center" class="wf wr fl">
    </td>
  </tr>
</table>
```

**r2col20**

Responsive two column stacking section with 20 pixels guttering
```html
<table cellpadding="20" cellspacing="0" border="0" width="$1" class="wf">
  <tr>
    <td align="center">
      <table width="660" border="0" cellspacing="0" cellpadding="0" class="wf">
        <tr class="wr" align="center">
          <td align="center" class="wf wr fl" width="320">
          $1
          </td>
          <td width="20" class="hide"></td>
          <td align="center" class="wf wr fl" width="320">
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table> 
```

**r3col**

Responsive three column stacking section
```html
<table cellpadding="0" cellspacing="0" border="0" width="$1" class="wf">
  <tr class="wr" align="center">
    <td align="center" class="wf wr fl">
    $2
    </td>
    <td align="center" class="wf wr fl">
    </td>
    <td align="center" class="wf wr fl">
    </td>
  </tr>
</table>
```

**r3col20**

Responsive three column stacking section with 20 pixels guttering
```html
<table cellpadding="20" cellspacing="0" border="0" width="700" class="wf">
  <tr>
    <td align="center">
      <table width="660" border="0" cellspacing="0" cellpadding="0" class="wf">
        <tr class="wr" align="center">
          <td align="center" class="wf wr fl" width="207">
          $1
          </td>
          <td width="20" class="hide"></td>
          <td align="center" class="wf wr fl" width="207">
          </td>
          <td width="20" class="hide"></td>
          <td align="center" class="wf wr fl" width="206">
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
```

**r4col**

Responsive four column stacking section
```html
<table cellpadding="0" cellspacing="0" border="0" width="$1" class="wf">
  <tr class="wr" align="center">
    <td align="center" class="wf wr fl">
    $2
    </td>
    <td align="center" class="wf wr fl">
    </td>
    <td align="center" class="wf wr fl">
    </td>
    <td align="center" class="wf wr fl">
    </td>
  </tr>
</table>
```

**r4col20**

Responsive four column stacking section with 20 pixels guttering
```html
<table cellpadding="20" cellspacing="0" border="0" width="700" class="wf">
  <tr>
    <td align="center">
      <table width="660" border="0" cellspacing="0" cellpadding="0" class="wf">
        <tr class="wr" align="center">
          <td align="center" class="wf wr fl" width="150">
          $1
          </td>
          <td width="20" class="hide"></td>
          <td align="center" class="wf wr fl" width="150">
          </td>
          <td width="20" class="hide"></td>
          <td align="center" class="wf wr fl" width="150">
          </td>
          <td width="20" class="hide"></td>
          <td align="center" class="wf wr fl" width="150">
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
```

**rbase**

Base HTML and CSS for a responsive email
```html
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html;charset=UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <meta name="format-detection" content="telephone=no">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="robots" content="noindex, nofollow">

  <title></title>

  <style type="text/css">
    body {width: 100% !important;}
    #outlook a {padding:0;}
    img { outline: none; text-decoration: none; }
    a img { border:none; }
    table td { border-collapse: collapse; }
    .appleLinksWhite a {color: #ffffff !important; text-decoration: underline;}
    *[class="gmail-fix"] {display: none !important;}
    /*Mobile*/
        @media only screen and (max-width: 639px) {
          *[class].maintable {width:100% !important;}
          *[class].bannerimg {width:100% !important; height: auto !important;}
          *[class].fl{float:left !important;}
          *[class].wr{display:block !important;}
          *[class].wf{width:100% !important;}
          *[class].wf10pb{width:100% !important; padding-bottom:10px !important;}
          *[class].wf10pt{width:100% !important; padding-top:10px !important;}
          *[class].wf10pl{width:100% !important; padding-left:10px !important}
          *[class].wf10pr{width:100% !important; padding-right:10px !important}
          *[class].wf10p{width:100% !important; padding:10px !important;}
          *[class].wf20p{width:100% !important; padding:20px !important;}
          *[class].hide{display:none !important;}
          *[class].delete{width:0px !important; height: 0px !important; font-size: 0px !important; line-height:0px !important;}
          *[class].tp{display: table-header-group !important; width:100%!important;}
          *[class].bm{display: table-footer-group !important; width:100%!important;}
          *[class].p{padding:20px;}
          *[class].half{width:50% !important;}
          *[class].textLeft {
            text-align: left !important;
          }
           *[class].textCenter {
            text-align: center !important;
          }
          *[class="show"] {
            display: block !important;
            margin: 0 !important;
            overflow: visible !important;
            width: auto !important;
            max-height: inherit !important;
            font-size: inherit !important;
            line-height: inherit !important
          }

          a[x-apple-data-detectors] {
            color: inherit !important;
            text-decoration: none !important;
            font-size: inherit !important;
            font-family: inherit !important;
            font-weight: inherit !important;
            line-height: inherit !important;
          }

  }
  </style>
</head>
<body style="min-width:100%; width: 100%; padding:0; margin:0; -webkit-text-size-adjust:none;" bgcolor="#ebebeb">
  <table height="100%" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td valign="top" align="center">

        $1

      </td>
    </tr>
    <tr class="gmail-fix">
      <td>
        <table cellpadding="0" cellspacing="0" border="0" align="center" width="640">
          <tr>
            <td style="line-height: 1px; min-width: 640px;">
              <img src="images/spacer.gif" width="640" height="1" style="display: block; max-height: 1px; min-height: 1px; min-width: 640px; width: 640px;"/>
              </td>
            </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

**rbutton**

A responsive button which expands to full width on mobile
```html
<table cellpadding="0" cellspacing="0" border="0" width="170" class="wf" height="35" bgcolor="#000001" style="border: solid 1px #000001; border-radius:10px;">
  <tr>
    <td valign="middle" style="font-family: 'Helvetica Neue', Helvetica, Arial; font-size:15px;"  align="center"><a href="" style="color:#ffffff; display: inline-block; text-decoration: none; text-transform:uppercase; line-height:32px; width:170px;">Button</a>
    </td>
  </tr>
</table>
```

**rimg**

A responsive full-width image
```html
<img src="images/img_$1.jpg" alt="" style="display: block; border: 0" border="0" class="bannerimg" width="$2" height="$3">
```

**rpre**

A responsive 50/50 email preheader
```html
<tr>
  <td>
    <table cellpadding="0" cellspacing="0" border="0" width="100%">
      <tr>
        <td width="50%" align="left" class="hide" style="font-family: sans-serif; font-size:12px; color: #3a3a3a; padding: 5px 0"></td>
        <td width="50%" align="right" style="font-family: sans-serif; font-size:12px">
          <a href="[VIEW_ONLINE_HTML]" style="color:#3a3a3a">View in browser</a> | <a href="[UNSUBSCRIPTION_LINK]" style="color:#3a3a3a">Unsubscribe</a>
        </td>
      </tr>
    </table>
  </td>
</tr>
```

**rtab**

A simple responsive table structure
```html
<table cellpadding="0" cellspacing="0" border="0" width="$1" class="wf">
  <tr>
    <td align="center">
      $2
    </td>
  </tr>
</table>
```

**rtl**

Right-to-left reverse responsive stacking
```html
<table width="$1" class="wf" border="0" cellpadding="0" cellspacing="0" align="center">
  <tr>
    <td dir="rtl">
      <table width="$2" class="wf" border="0" cellpadding="0" cellspacing="0" align="right">
        <tr>
          <td dir="ltr">$4</td>
        </tr>
      </table>
      <!--[if mso]></td><td><![endif]-->
      <table width="$3" class="wf" border="0" cellpadding="0" cellspacing="0" align="left">
        <tr>
          <td dir="ltr">

          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
```

**rnor**

Left to right stacking
```html
<table cellpadding="0" cellspacing="0" border="0" width="640" class="wf" bgcolor="#ffffff">
  <tr align="center">
    <td align="center" class="tp">
      <a href=""><img src="images/img_$1.jpg" alt="" style="display: block; border: 0" border="0" class="bannerimg" width="320" height="$3"></a>
    </td>
    <td align="center" class="bm">
      <a href=""><img src="images/img_$2.jpg" alt="" style="display: block; border: 0" border="0" class="bannerimg" width="320" height="$3"></a>
    </td>
  </tr>
</table>
```

**rrev**

Right to left stacking
```html
<table cellpadding="0" cellspacing="0" border="0" width="640" class="wf" bgcolor="#ffffff">
  <tr align="center">
    <td align="center" class="bm">
      <a href=""><img src="images/img_$1.jpg" alt="" style="display: block; border: 0" border="0" class="bannerimg" width="320" height="$3"></a>
    </td>
    <td align="center" class="tp">
      <a href=""><img src="images/img_$2.jpg" alt="" style="display: block; border: 0" border="0" class="bannerimg" width="320" height="$3"></a>
    </td>
  </tr>
</table>
```

---

Animation Snippets
------

Animation snippets are all prefixed with the letters 'ani'

**aniband**

Rubber banding CSS3 animation effect
```css
.band {
  -webkit-animation: rubberBand 1s linear infinite;
  -moz-animation: rubberBand 1s linear infinite;
  -o-animation: rubberBand 1s linear infinite;
  }

@-webkit-keyframes rubberBand {
  0% {
    -webkit-transform: scale3d(1, 1, 1);
            transform: scale3d(1, 1, 1);
  }

  30% {
    -webkit-transform: scale3d(1.25, 0.75, 1);
            transform: scale3d(1.25, 0.75, 1);
  }

  40% {
    -webkit-transform: scale3d(0.75, 1.25, 1);
            transform: scale3d(0.75, 1.25, 1);
  }

  50% {
    -webkit-transform: scale3d(1.15, 0.85, 1);
            transform: scale3d(1.15, 0.85, 1);
  }

  65% {
    -webkit-transform: scale3d(.95, 1.05, 1);
            transform: scale3d(.95, 1.05, 1);
  }

  75% {
    -webkit-transform: scale3d(1.05, .95, 1);
            transform: scale3d(1.05, .95, 1);
  }

  100% {
    -webkit-transform: scale3d(1, 1, 1);
            transform: scale3d(1, 1, 1);
  }
}

@keyframes rubberBand {
  0% {
    -webkit-transform: scale3d(1, 1, 1);
            transform: scale3d(1, 1, 1);
  }

  30% {
    -webkit-transform: scale3d(1.25, 0.75, 1);
            transform: scale3d(1.25, 0.75, 1);
  }

  40% {
    -webkit-transform: scale3d(0.75, 1.25, 1);
            transform: scale3d(0.75, 1.25, 1);
  }

  50% {
    -webkit-transform: scale3d(1.15, 0.85, 1);
            transform: scale3d(1.15, 0.85, 1);
  }

  65% {
    -webkit-transform: scale3d(.95, 1.05, 1);
            transform: scale3d(.95, 1.05, 1);
  }

  75% {
    -webkit-transform: scale3d(1.05, .95, 1);
            transform: scale3d(1.05, .95, 1);
  }

  100% {
    -webkit-transform: scale3d(1, 1, 1);
            transform: scale3d(1, 1, 1);
  }
```

**anibounce**

Bouncing CSS3 animation effect
```css
.bounce {
  -webkit-animation: bounce 1s linear infinite;
  -moz-animation: bounce 1s linear infinite;
  -o-animation: bounce 1s linear infinite;
  }

  @-webkit-keyframes bounce {
  0%, 20%, 53%, 80%, 100% {
    -webkit-transition-timing-function: cubic-bezier(0.215, 0.610, 0.355, 1.000);
            transition-timing-function: cubic-bezier(0.215, 0.610, 0.355, 1.000);
    -webkit-transform: translate3d(0,0,0);
            transform: translate3d(0,0,0);
  }

  40%, 43% {
    -webkit-transition-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
            transition-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
    -webkit-transform: translate3d(0, -30px, 0);
            transform: translate3d(0, -30px, 0);
  }

  70% {
    -webkit-transition-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
            transition-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
    -webkit-transform: translate3d(0, -15px, 0);
            transform: translate3d(0, -15px, 0);
  }

  90% {
    -webkit-transform: translate3d(0,-4px,0);
            transform: translate3d(0,-4px,0);
  }
  }
  @keyframes bounce {
    0%, 20%, 53%, 80%, 100% {
      -webkit-transition-timing-function: cubic-bezier(0.215, 0.610, 0.355, 1.000);
              transition-timing-function: cubic-bezier(0.215, 0.610, 0.355, 1.000);
      -webkit-transform: translate3d(0,0,0);
              transform: translate3d(0,0,0);
    }

    40%, 43% {
      -webkit-transition-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
              transition-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
      -webkit-transform: translate3d(0, -30px, 0);
              transform: translate3d(0, -30px, 0);
    }

    70% {
      -webkit-transition-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
              transition-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
      -webkit-transform: translate3d(0, -15px, 0);
              transform: translate3d(0, -15px, 0);
    }

    90% {
      -webkit-transform: translate3d(0,-4px,0);
              transform: translate3d(0,-4px,0);
    }
  }
```

**anifade**

Fading in and out CSS3 animation effect
```css
.fade {
  -webkit-animation: fadeIn 5s linear infinite;
  -moz-animation: fadeIn 5s linear infinite;
  -o-animation: fadeIn 5s linear infinite;
  }
  @-webkit-keyframes fadeIn {
  0% {opacity: 0;}
  50% {opacity: 1;}
  100% {opacity: 0;}
```

**aniflip**

Continuous flipping CSS3 animation effect
```css
.flip {
    -webkit-animation: flip 2s linear infinite;
    -moz-animation: flip 2s linear infinite;
    -o-animation: flip 2s linear infinite;
    }

  @-webkit-keyframes flip {     
  0% {
    -webkit-transform: perspective(400px) rotate3d(0, 1, 0, -360deg);
            transform: perspective(400px) rotate3d(0, 1, 0, -360deg);
    -webkit-animation-timing-function: ease-out;
            animation-timing-function: ease-out;
  }

  40% {
    -webkit-transform: perspective(400px) translate3d(0, 0, 150px) rotate3d(0, 1, 0, -190deg);
            transform: perspective(400px) translate3d(0, 0, 150px) rotate3d(0, 1, 0, -190deg);
    -webkit-animation-timing-function: ease-out;
            animation-timing-function: ease-out;
  }

  50% {
    -webkit-transform: perspective(400px) translate3d(0, 0, 150px) rotate3d(0, 1, 0, -170deg);
            transform: perspective(400px) translate3d(0, 0, 150px) rotate3d(0, 1, 0, -170deg);
    -webkit-animation-timing-function: ease-in;
            animation-timing-function: ease-in;
  }

  80% {
    -webkit-transform: perspective(400px) scale3d(.95, .95, .95);
            transform: perspective(400px) scale3d(.95, .95, .95);
    -webkit-animation-timing-function: ease-in;
            animation-timing-function: ease-in;
  }

  100% {
    -webkit-transform: perspective(400px);
            transform: perspective(400px);
    -webkit-animation-timing-function: ease-in;
            animation-timing-function: ease-in;
  }
  }

@keyframes flip {
  0% {
    -webkit-transform: perspective(400px) rotate3d(0, 1, 0, -360deg);
            transform: perspective(400px) rotate3d(0, 1, 0, -360deg);
    -webkit-animation-timing-function: ease-out;
            animation-timing-function: ease-out;
  }

  40% {
    -webkit-transform: perspective(400px) translate3d(0, 0, 150px) rotate3d(0, 1, 0, -190deg);
            transform: perspective(400px) translate3d(0, 0, 150px) rotate3d(0, 1, 0, -190deg);
    -webkit-animation-timing-function: ease-out;
            animation-timing-function: ease-out;
  }

  50% {
    -webkit-transform: perspective(400px) translate3d(0, 0, 150px) rotate3d(0, 1, 0, -170deg);
            transform: perspective(400px) translate3d(0, 0, 150px) rotate3d(0, 1, 0, -170deg);
    -webkit-animation-timing-function: ease-in;
            animation-timing-function: ease-in;
  }

  80% {
    -webkit-transform: perspective(400px) scale3d(.95, .95, .95);
            transform: perspective(400px) scale3d(.95, .95, .95);
    -webkit-animation-timing-function: ease-in;
            animation-timing-function: ease-in;
  }

  100% {
    -webkit-transform: perspective(400px);
            transform: perspective(400px);
    -webkit-animation-timing-function: ease-in;
            animation-timing-function: ease-in;
  }
```

**anihinge**

Hinge/door-like CSS3 animation hover effect
```css
.hinge:hover {
  -webkit-animation: hinge 2s linear 1;
  -moz-animation: hinge 2s linear 1;
  -o-animation: hinge 2s linear 1;
  }


  @-webkit-keyframes hinge {
  0% {
    -webkit-transform-origin: top left;
            transform-origin: top left;
    -webkit-animation-timing-function: ease-in-out;
            animation-timing-function: ease-in-out;
  }

  20%, 60% {
    -webkit-transform: rotate3d(0, 0, 1, 80deg);
            transform: rotate3d(0, 0, 1, 80deg);
    -webkit-transform-origin: top left;
            transform-origin: top left;
    -webkit-animation-timing-function: ease-in-out;
            animation-timing-function: ease-in-out;
  }

  40%, 80% {
    -webkit-transform: rotate3d(0, 0, 1, 60deg);
            transform: rotate3d(0, 0, 1, 60deg);
    -webkit-transform-origin: top left;
            transform-origin: top left;
    -webkit-animation-timing-function: ease-in-out;
            animation-timing-function: ease-in-out;
    opacity: 1;
  }

  100% {
    -webkit-transform: translate3d(0, 700px, 0);
            transform: translate3d(0, 700px, 0);
    opacity: 0;
  }
}

@keyframes hinge {
  0% {
    -webkit-transform-origin: top left;
            transform-origin: top left;
    -webkit-animation-timing-function: ease-in-out;
            animation-timing-function: ease-in-out;
  }

  20%, 60% {
    -webkit-transform: rotate3d(0, 0, 1, 80deg);
            transform: rotate3d(0, 0, 1, 80deg);
    -webkit-transform-origin: top left;
            transform-origin: top left;
    -webkit-animation-timing-function: ease-in-out;
            animation-timing-function: ease-in-out;
  }

  40%, 80% {
    -webkit-transform: rotate3d(0, 0, 1, 60deg);
            transform: rotate3d(0, 0, 1, 60deg);
    -webkit-transform-origin: top left;
            transform-origin: top left;
    -webkit-animation-timing-function: ease-in-out;
            animation-timing-function: ease-in-out;
    opacity: 1;
  }

  100% {
    -webkit-transform: translate3d(0, 700px, 0);
            transform: translate3d(0, 700px, 0);
    opacity: 0;
  }
```

**anipulse** 

Looping pulsating CSS3 animation effect
```css
.pulse {
  -webkit-animation: pulsate 2s linear infinite;
  -moz-animation: pulsate 2s linear infinite;
  -o-animation: pulsate 2s linear infinite;
  }
  @-webkit-keyframes pulsate {
      0% {-webkit-transform: scale(1);}
      50% {-webkit-transform: scale(0.8);}
      100% {-webkit-transform: scale(1);}
```

**anirotate**

Spinning CSS3 animation effect
```css
.rotate {
    -webkit-animation:spin 20s linear infinite;
    -moz-animation:spin 20s linear infinite;
    animation:spin 20s linear infinite;
    }
    @-moz-keyframes spin { 100% { -moz-transform: rotate(360deg); } }
    @-webkit-keyframes spin { 100% { -webkit-transform: rotate(360deg); } }
    @keyframes spin { 100% { -webkit-transform: rotate(360deg); transform:rotate(360deg); } 
```

**anishowoff**

Flashy pop-out CSS3 animation effect
```css
.showOff {
  -webkit-animation: tada 2s linear infinite;
  -moz-animation: tada 2s linear infinite;
  -o-animation: tada 2s linear infinite;
  }
  @-webkit-keyframes tada {
  0% {
    -webkit-transform: scale3d(1, 1, 1);
            transform: scale3d(1, 1, 1);
  }

  10%, 20% {
    -webkit-transform: scale3d(.9, .9, .9) rotate3d(0, 0, 1, -3deg);
            transform: scale3d(.9, .9, .9) rotate3d(0, 0, 1, -3deg);
  }

  30%, 50%, 70%, 90% {
    -webkit-transform: scale3d(1.1, 1.1, 1.1) rotate3d(0, 0, 1, 3deg);
            transform: scale3d(1.1, 1.1, 1.1) rotate3d(0, 0, 1, 3deg);
  }

  40%, 60%, 80% {
    -webkit-transform: scale3d(1.1, 1.1, 1.1) rotate3d(0, 0, 1, -3deg);
            transform: scale3d(1.1, 1.1, 1.1) rotate3d(0, 0, 1, -3deg);
  }

  100% {
    -webkit-transform: scale3d(1, 1, 1);
            transform: scale3d(1, 1, 1);
  }
```

**aniswing**

Continous swinging CSS3 animation effect
```css
.swing {
  -webkit-animation: swing 2s linear infinite;
  -moz-animation: swing 2s linear infinite;
  -o-animation: swing 2s linear infinite;
  }

  @-webkit-keyframes swing {
  20% {
    -webkit-transform: rotate3d(0, 0, 1, 15deg);
            transform: rotate3d(0, 0, 1, 15deg);
  }

  40% {
    -webkit-transform: rotate3d(0, 0, 1, -10deg);
            transform: rotate3d(0, 0, 1, -10deg);
  }

  60% {
    -webkit-transform: rotate3d(0, 0, 1, 5deg);
            transform: rotate3d(0, 0, 1, 5deg);
  }

  80% {
    -webkit-transform: rotate3d(0, 0, 1, -5deg);
            transform: rotate3d(0, 0, 1, -5deg);
  }

  100% {
    -webkit-transform: rotate3d(0, 0, 1, 0deg);
            transform: rotate3d(0, 0, 1, 0deg);
  }
  }

  @keyframes swing {
    20% {
      -webkit-transform: rotate3d(0, 0, 1, 15deg);
              transform: rotate3d(0, 0, 1, 15deg);
    }

    40% {
      -webkit-transform: rotate3d(0, 0, 1, -10deg);
              transform: rotate3d(0, 0, 1, -10deg);
    }

    60% {
      -webkit-transform: rotate3d(0, 0, 1, 5deg);
              transform: rotate3d(0, 0, 1, 5deg);
    }

    80% {
      -webkit-transform: rotate3d(0, 0, 1, -5deg);
              transform: rotate3d(0, 0, 1, -5deg);
    }

    100% {
      -webkit-transform: rotate3d(0, 0, 1, 0deg);
              transform: rotate3d(0, 0, 1, 0deg);
    }
```


---

Static Snippets
------

**sback**

Bullet proof backgrounds for static emails
```html
<td background="$1.jpg" bgcolor="$2" width="600" height="$3" valign="middle">
  <!--[if gte mso 9]>
  <v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:$3px;">
    <v:fill type="tile" src="$1" color="$2" />
    <v:textbox inset="0,0,0,0">
  <![endif]-->
    <div>

    <!-- Your code -->

    </div>
  <!--[if gte mso 9]>
    </v:textbox>
  </v:rect>
  <![endif]-->
</td>
```

**sbase**

The base HTML and CSS for a static email
```html
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html;charset=UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <meta name="format-detection" content="telephone=no">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="robots" content="noindex, nofollow">

  <title>{?$subject_line?}</title>

  <style type="text/css">
    body {width: 100% !important;}
    #outlook a {padding:0;}
    img { outline: none; text-decoration: none; }
    a img { border:none; }
    table td { border-collapse: collapse; }
    .appleLinksWhite a {color: #ffffff !important; text-decoration: underline;}

  </style>
</head>
<body style="padding:0; margin:0" bgcolor="#ebebeb">
  <table height="100%" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#ebebeb">
    <tr>
      <td valign="top" align="center">

      $1

      </td>
    </tr>
  </table>

<div style="display:none; white-space:nowrap; font:15px courier; line-height:0;">
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
</div>

</body>

</html>
```

**simg**

A static full-width image
```html
<tr>
  <td align="center">
    <img src="images/img_$1.jpg" alt="" style="display: block; border: 0">
  </td>
</tr>
```

**stab**

A simple static table structure
```html
<table cellpadding="0" cellspacing="0" border="0" width="$1">
  <tr>
    <td>
      $2
    </td>
  </tr>
</table>
```

---

Button Snippets
------

**buttonf**

A filled bullet proof button
```html
<table cellpadding="0" cellspacing="0" border="0" width="170" height="35" bgcolor="#000001" style="border: solid 1px #000001; border-radius:10px;">
  <tr>
    <td valign="middle" style="font-family: 'Helvetica Neue', Helvetica, Arial; font-size:15px;"  align="center"><a href="" style="color:#ffffff; display: inline-block; text-decoration: none; text-transform:uppercase; line-height:32px; width:170px;">Button</a>
    </td>
  </tr>
</table>
```

**buttont**

A transparent bordered button
```html
<table cellpadding="0" cellspacing="0" border="0" width="170" height="35" style="border: solid 1px #2e2e2e;">
  <tr>
    <td valign="middle" style="font-family: 'Helvetica Neue', Helvetica, Arial; font-size:15px;"  align="center"><a href="" style="color:#2e2e2e; display: inline-block; text-decoration: none; text-transform:uppercase; line-height:32px; width:170px;">Button</a>
    </td>
  </tr>
</table>
```

---

Spongy Snippets
------

**sp2col**

2 column stacking spongey section
```html
<!--[if (gte mso 9)|(IE)]>
<table width="650" align="center" style="border-spacing:0;font-family:sans-serif;color:#ffffff;" cellpadding="0" cellspacing="0" border="0">
<tr>
<td style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
<![endif]-->
<table class="outer" align="center" style="border-spacing:0;font-family:sans-serif;color:#333333;Margin:0 auto;width:100%;max-width:650px;background-color:#ffffff;" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td class="two-column inner5" style="padding:0 25px;text-align:center;font-size:0;" >
      <!--[if (gte mso 9)|(IE)]>
      <table width="600" style="border-spacing:0;font-family:sans-serif;color:#333333;" >
      <tr>
      <td width="300" valign="top" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <div class="column" style="width:100%;max-width:300px;display:inline-block;vertical-align:top;" >
        <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="0" cellspacing="0" border="0">
          <tr>            
            <td style="padding:5px;">
              <table class="contents" style="border-spacing:0;font-family:sans-serif;color:#333333;width:100%;font-size:14px;text-align:left;" >
                
                <tr>
                  <td align="center">1</td>
                </tr>
              </table>
            </td>                
          </tr>
        </table>
      </div>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      <td width="300" valign="top" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <div class="column" style="width:100%;max-width:300px;display:inline-block;vertical-align:top;" >
        <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="0" cellspacing="0" border="0">
          <tr>
            
            <td style="padding:5px;">
              <table class="contents" style="border-spacing:0;font-family:sans-serif;color:#333333;width:100%;font-size:14px;text-align:left;" >
                <tr>
                  <td align="center">2</td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </div>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      </tr>
      </table>
      <![endif]-->
    </td>
  </tr>
  <tr>
      <td height="20" style="font-size: 10px; line-height: 10px;">&nbsp;</td>
  </tr>

</table>
<!--[if (gte mso 9)|(IE)]>
</td>
</tr>
</table>
<![endif]-->
```

**sp3col**

3 column stacking spongy section
```html
<!--[if (gte mso 9)|(IE)]>
<table width="650" align="center" style="border-spacing:0;font-family:sans-serif;color:#ffffff;" border="0" cellspacing="0" cellpadding="0">
<tr>
<td style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
<![endif]-->
<table class="outer" align="center" style="border-spacing:0;font-family:sans-serif;color:#333333;Margin:0 auto;width:100%;max-width:650px;background-color:#ffffff;" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td class="two-column inner5" style="padding-top:0;padding-bottom:0;padding-right:25px;padding-left:25px;text-align:center;font-size:0;" >
      <!--[if (gte mso 9)|(IE)]>
      <table width="600" style="border-spacing:0;font-family:sans-serif;color:#333333;" border="0" cellspacing="0" cellpadding="0">
      <tr>
      <td width="200" valign="top" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <div class="column" style="width:100%;max-width:200px;display:inline-block;vertical-align:top;" >
        <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="5" cellspacing="0" border="0">
          <tr>
            <td>
              <table class="contents" style="border-spacing:0;font-family:sans-serif;color:#333333;width:100%;font-size:14px;text-align:left;" cellspacing="0" cellpadding="5" border="0">
                <tr>
                  <td align="left" style="font-size:15px;color:#000001;font-family:Helvetica, arial, sans-serif;font-weight:bold;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" ><img src="images/img-1.jpg" border="0" style="display:block;border-width:0;width:100%;max-width:190px;height:auto;" ></td>
                </tr>
                
              </table>
            </td>
            
          </tr>
        </table>
      </div>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      <td width="200" valign="top" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <div class="column" style="width:100%;max-width:200px;display:inline-block;vertical-align:top;" >
        <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="5" cellspacing="0" border="0">
          <tr>
            <td>
              <table class="contents" style="border-spacing:0;font-family:sans-serif;color:#333333;width:100%;font-size:14px;text-align:left;" cellspacing="0" cellpadding="5" border="0">
                <tr>
                  <td align="left" style="font-size:15px;color:#000001;font-family:Helvetica, arial, sans-serif;font-weight:bold;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" ><img src="images/img-2.jpg" border="0" style="display:block;border-width:0;width:100%;max-width:190px;height:auto;" ></td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </div>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      <td width="200" valign="top" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <div class="column" style="width:100%;max-width:200px;display:inline-block;vertical-align:top;" >
        <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="5" cellspacing="0" border="0">
          <tr>  
            <td>
              <table class="contents" style="border-spacing:0;font-family:sans-serif;color:#333333;width:100%;font-size:14px;text-align:left;" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="left" style="font-size:15px;color:#000001;font-family:Helvetica, arial, sans-serif;font-weight:bold;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" ><img src="images/img-3.jpg" border="0" style="display:block;border-width:0;width:100%;max-width:190px;height:auto;" width="190" height="190" ></td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </div>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      </tr>
      </table>
      <![endif]-->
    </td>
  </tr>
  <tr>
      <td height="20" style="font-size:10px;line-height:10px;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >&nbsp;</td>
  </tr>

</table>
<!--[if (gte mso 9)|(IE)]>
</td>
</tr>
</table>
<![endif]-->
```

**sp4col**

4 column stacking spongy section
```html
<!--[if (gte mso 9)|(IE)]>
<table width="650" align="center" style="border-spacing:0;font-family:sans-serif;color:#ffffff;" border="0" cellspacing="0" cellpadding="0">
<tr>
<td style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
<![endif]-->
<table class="outer" align="center" style="border-spacing:0;font-family:sans-serif;color:#333333;Margin:0 auto;width:100%;max-width:650px;background-color:#ffffff;" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td class="two-column inner5" style="padding-top:0;padding-bottom:0;padding-right:25px;padding-left:25px;text-align:center;font-size:0;" >
      <!--[if (gte mso 9)|(IE)]>
      <table width="600" style="border-spacing:0;font-family:sans-serif;color:#333333;" border="0" cellspacing="0" cellpadding="0">
      <tr>
      <td width="150" valign="top" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <div class="column" style="width:100%;max-width:150px;display:inline-block;vertical-align:top;" >
        <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="5" cellspacing="0" border="0">
          <tr>
            <td>
              <table class="contents" style="border-spacing:0;font-family:sans-serif;color:#333333;width:100%;font-size:14px;text-align:left;" cellspacing="0" cellpadding="5" border="0">
                <tr>
                  <td align="left" style="font-size:15px;color:#000001;font-family:Helvetica, arial, sans-serif;font-weight:bold;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" ><img src="images/img-1.jpg" border="0" style="display:block;border-width:0;width:100%;max-width:140px;height:auto;" ></td>
                </tr>
                
              </table>
            </td>
            
          </tr>
        </table>
      </div>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      <td width="150" valign="top" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <div class="column" style="width:100%;max-width:150px;display:inline-block;vertical-align:top;" >
        <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="5" cellspacing="0" border="0">
          <tr>
            <td>
              <table class="contents" style="border-spacing:0;font-family:sans-serif;color:#333333;width:100%;font-size:14px;text-align:left;" cellspacing="0" cellpadding="5" border="0">
                <tr>
                  <td align="left" style="font-size:15px;color:#000001;font-family:Helvetica, arial, sans-serif;font-weight:bold;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" ><img src="images/img-2.jpg" border="0" style="display:block;border-width:0;width:100%;max-width:140px;height:auto;" ></td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </div>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      <td width="150" valign="top" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <div class="column" style="width:100%;max-width:150px;display:inline-block;vertical-align:top;" >
        <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="5" cellspacing="0" border="0">
          <tr>  
            <td>
              <table class="contents" style="border-spacing:0;font-family:sans-serif;color:#333333;width:100%;font-size:14px;text-align:left;" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="left" style="font-size:15px;color:#000001;font-family:Helvetica, arial, sans-serif;font-weight:bold;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" ><img src="images/img-3.jpg" border="0" style="display:block;border-width:0;width:100%;max-width:140px;height:auto;" width="140" height="140" ></td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </div>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      <td width="150" valign="top" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <div class="column" style="width:100%;max-width:150px;display:inline-block;vertical-align:top;" >
        <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="5" cellspacing="0" border="0">
          <tr>
            <td>
              <table class="contents" style="border-spacing:0;font-family:sans-serif;color:#333333;width:100%;font-size:14px;text-align:left;" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="left" style="font-size:15px;color:#000001;font-family:Helvetica, arial, sans-serif;font-weight:bold;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" ><img src="images/img-4.jpg" border="0" style="display:block;border-width:0;width:100%;max-width:140px;height:auto;" ></td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </div>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      </tr>
      </table>
      <![endif]-->
    </td>
  </tr>
  <tr>
      <td height="20" style="font-size:10px;line-height:10px;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >&nbsp;</td>
  </tr>

</table>
<!--[if (gte mso 9)|(IE)]>
</td>
</tr>
</table>
<![endif]-->
```

**spbase**

The base HTML and CSS for a spongy email
```html
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <!--[if !mso]><!-->
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <!--<![endif]-->
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{??}</title>
  <style type="text/css">



@media screen and (max-width: 400px) {
  .two-column .column,
  .three-column .column {
    max-width: 100% !important;
  }
  .two-column img {
    max-width: 100% !important;
  }
  .three-column img {
    max-width: 50% !important;
  }
}

@media screen and (min-width: 401px) and (max-width: 620px) {
  .three-column .column {
    max-width: 33% !important;
  }
  .two-column .column {
    max-width: 50% !important;
  }
}
  </style>
  <!--[if (gte mso 9)|(IE)]>
  <style type="text/css">
    table {border-collapse: collapse !important !important;}
  </style>
  <![endif]-->
</head>
<body style="Margin:0;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;min-width:100%;" >

  <center class="wrapper" style="width:100%;table-layout:fixed;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;" >
    <div class="webkit" style="max-width:$1px;">

      <!--[if (gte mso 9)|(IE)]>
      <table width="$1" align="center" style="border-spacing:0;font-family:sans-serif;color:#333333;" border="0" cellspacing="0" cellpadding="0">
      <tr>
      <td style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <![endif]-->
      <table class="outer" align="center" style="border-spacing:0;font-family:sans-serif;color:#333333;Margin:0 auto;width:100%;max-width:$1px;" cellpadding="0" cellspacing="0" border="0">
        <tr>
          $2
        </tr>
      </table>
      <!--[if (gte mso 9)|(IE)]>
      </td>
      </tr>
      </table>
      <![endif]-->
    </div>
  </center>
</body>
</html>
```

**spimg**

A full-width spongy image
```html
<!--[if (gte mso 9)|(IE)]>
</td>
</tr>
</table>
<![endif]-->
<!--[if (gte mso 9)|(IE)]>
<table width="$1" align="center" style="border-spacing:0;font-family:sans-serif;color:#333333;" border="0" cellspacing="0" cellpadding="0">
<tr>
<td style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
<![endif]-->
<table class="outer" align="center" style="border-spacing:0;font-family:sans-serif;color:#333333;Margin:0 auto;width:100%;max-width:650px;background-color:#ffffff;" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td class="full-width-image" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <img src="images/hero-2.jpg" width="$1" alt="" style="border-width:0;width:100%;max-width:$1px;height:auto;" />
    </td>
  </tr>
  <tr>
      <td height="20" style="font-size:20px;line-height:20px;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >&nbsp;</td>
  </tr>
</table>
<!--[if (gte mso 9)|(IE)]>
</td>
</tr>
</table>
<![endif]-->
```

**sptitle**

A full-width spongy title/text area
```html
<!--[if (gte mso 9)|(IE)]>
<table width="650" align="center" style="border-spacing:0;font-family:sans-serif;color:#333333;" border="0" cellspacing="0" cellpadding="0">
<tr>
<td style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
<![endif]-->
<table class="outer" align="center" style="border-spacing:0;font-family:sans-serif;color:#333333;Margin:0 auto;width:100%;max-width:650px;background-color:#ffffff;" cellpadding="0" cellspacing="0" border="0">
  <tr>
      <td height="20" style="font-size:20px;line-height:20px;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >&nbsp;</td>
  </tr>
  <tr>
    <td class="one-column" style="padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >
      <table width="100%" style="border-spacing:0;font-family:sans-serif;color:#333333;" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td class="inner contents" style="width:100%;text-align:left;font-family:Helvetica, Arial, sans-serif;font-size:32px;color:#000001;font-weight:bold;padding-top:30px;padding-bottom:0px;padding-right:30px;padding-left:30px;" >
            $1
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
      <td height="20" style="font-size:20px;line-height:20px;padding-top:0;padding-bottom:0;padding-right:0;padding-left:0;" >&nbsp;</td>
  </tr>
</table>
<!--[if (gte mso 9)|(IE)]>
</td>
</tr>
</table>
<![endif]-->
```

---

General Snippets
------

**helv**

Helvetica font-stack
```css
font-family: Helvetica, Arial, 'Lucida Grande', sans-serif;
```

**georgia**

Georgia font-stack
```css
font-family: Georgia, Times, 'Times New Roman', serif;
```

**arial**

Arial font-stack
```css
font-family: Arial, sans-serif;
```

**calibri**

Calibri font-stack
```css
font-family: Calibri,Candara,Segoe,Segoe UI,Optima,Arial,sans-serif;
```

**verdana**

Verdana font-stack
```css
font-family: Verdana,Geneva,sans-serif; 
```

**tahoma**

Tahoma font-stack
```css
font-family: Tahoma,Verdana,Segoe,sans-serif; 
```

**times**

Times new roman font-stack
```css
font-family: Times New Roman,'Times New Roman',Times,Baskerville,Georgia,serif; 
```

**showhide**

Content swapping technique between mobile/desktop
```html
<a href="$4">
<img src="$1" class="hide" style="display: block;" border="0" alt="$2" />
<!--[if !mso]><!-->
<div class="show" style="font-size: 0%; max-height: 0; width:0px; overflow: hidden; display: none;"><img  src="$3" style="display: block;" /></div>
<!--<![endif]-->
</a>
```

**space**

Add a spacer row
```html
<tr>
    <td height="$1" style="font-size: $1px; line-height: $1px;">&nbsp;</td>
</tr>
```

**td10**

A 10 pixel wide cell
```html
<td width="10"></td>
```

**td20**

A 20 pixel wide cell
```html
<td width="20"></td>
```

**tv**

table row + cell
```html
<tr>
  <td align="center">$1</td>
</tr>
```

**tvl**

table row + cell
```html
<tr>
  <td align="left">$1</td>
</tr>
```

**tvr**

table row + cell
```html
<tr>
  <td align="right">$1</td>
</tr>
```

---
