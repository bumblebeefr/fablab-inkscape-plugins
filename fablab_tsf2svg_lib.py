import re
import logging
import os
import tempfile
from fablab_lib import convert_command
import base64
from os import path
import hashlib
from datetime import datetime
import errno
import webbrowser
from string import Template
import math
import sys

headers_re = {
    'ProcessMode': re.compile('<ProcessMode: (.*)>'),
    'Size': re.compile('<Size: ([0-9\.]*);([0-9\.]*)>'),
    'MaterialGroup': re.compile('<MaterialGroup: (.*)>'),
    'MaterialName': re.compile('<MaterialName: (.*)>'),
    'JobName': re.compile('<JobName: (.*)>'),
    'JobNumber': re.compile('<JobNumber: ([0-9]*)>'),
    'Resolution': re.compile('<Resolution: ([0-9]*)>'),
    'LayerParameter': re.compile('<LayerParameter: ([0-9]*);([0-9\.]*)>'),
    'StampShoulder': re.compile('<StampShoulder: (.*)>'),
    'Cutline': re.compile('<Cutline: (.*)>'),
}
headers_transfo = {
    'ProcessMode': lambda x: x[0],
    'Size': lambda x: {'width': float(x[0]), 'height': float(x[1])},
    'MaterialGroup': lambda x: x[0].decode('iso-8859-1'),
    'MaterialName': lambda x: x[0].decode('iso-8859-1'),
    'JobName': lambda x: x[0].decode('iso-8859-1'),
    'JobNumber': lambda x: int(x[0]),
    'Resolution': lambda x: int(x[0]),
    'LayerParameter': lambda x: {'layers': int(x[0]), 'adjustment': float(x[1])},
    'StampShoulder': lambda x: x[0],
    'Cutline': lambda x: x[0],
}
StampShoulders = {
    "flat": "Bord plat",
    "medium": "Bord moyen",
    "steep": "Bord raide",
}

bmp_re = re.compile('<STBmp: (.*)>BM(.*)<EOBmp>', re.S)
polygones_re = re.compile('<DrawPolygon: ([0-9;]*)>')

TROTEC_COLORS = [
    '#ff0000',
    '#0000ff',
    '#336699',
    '#00ffff',
    '#00ff00',
    '#009933',
    '#006633',
    '#999933',
    '#996633',
    '#663300',
    '#660066',
    '#9900cc',
    '#ff00ff',
    '#ff6600',
    '#ffff00'
]

HTML_TEMPLATE = Template('''
<html>
<head>
<title>$jobname</title>
<style>
body{
    overflow:hidden;
    background-color:#CCC;
    font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;
    font-size:10pt;
}
table{
    font-size:9pt;
}
#preview{
display: inline;
width: 100%;
height: 100%;
overflow:visible!important;
}
.svg-pan-zoom_viewport>rect{
    fill:#FFF!important;
    box-shadow: 1px 1px 12px #333;
    -webkit-filter: drop-shadow( 1px 1px 12px #333 );
    filter: drop-shadow( 1px 1px 12px #333 );
}
#container{
    background-color:#CCC;
    position:absolute;
    top:10px;
    left:10px;
    opacity:0;
}
#summary{
    position:absolute;
    top:10px;
    left:10px;
    width:350px;
    border:dotted 1px #444;
    background-color:rgba(255,255,255,130);
    opacity:0.6;
    padding:10px;
}
#summary>div{
    font-size:1.3em;
    font-weight:bold;
    text-align:center;
}
#summary:hover{
    opacity:1;
}
li{
    margin-bottom: 3px
}
em{
    font-size:8.5pt;
    font-weight:normal;
}
</style>
</head>
<body>
<div style="width:1024px; height:768px;" id="container">
    $svg
</div>
<div id="summary">
    <div>Fichier pr&ecirc;t pour la d&eacute;coupe</div>
    $export_time
    <br>
        <ul>
        <li><strong>Nom du job : </strong> $jobname </li>
        <li><strong>Mat&eacute;riau : </strong> $material_group &raquo; $material_name </li>
        <li><strong>Dimensions : </strong> $size </li>
        <li><strong>R&eacute;solution : </strong> $resolution </li>
        $colors
        <li><strong>Gravure : </strong> $engraving </li>
        <li><strong>Poid : </strong> $file_size </li>
    </ul>
</div>
<script>
// svg-pan-zoom v3.2.6
// https://github.com/ariutta/svg-pan-zoom
!function t(e,o,n){function i(r,a){if(!o[r]){if(!e[r]){var l="function"==typeof require&&require;if(!a&&l)return l(r,!0);if(s)return s(r,!0);var u=new Error("Cannot find module '"+r+"'");throw u.code="MODULE_NOT_FOUND",u}var h=o[r]={exports:{}};e[r][0].call(h.exports,function(t){var o=e[r][1][t];return i(o?o:t)},h,h.exports,t,e,o,n)}return o[r].exports}for(var s="function"==typeof require&&require,r=0;r<n.length;r++)i(n[r]);return i}({1:[function(t,e,o){var n=t("./svg-pan-zoom.js");!function(t,o){"function"==typeof define&&define.amd?define("svg-pan-zoom",function(){return n}):"undefined"!=typeof e&&e.exports&&(e.exports=n,t.svgPanZoom=n)}(window,document)},{"./svg-pan-zoom.js":4}],2:[function(t,e,o){var n=t("./svg-utilities");e.exports={enable:function(t){var e=t.svg.querySelector("defs");e||(e=document.createElementNS(n.svgNS,"defs"),t.svg.appendChild(e));var o=document.createElementNS(n.svgNS,"style");o.setAttribute("type","text/css"),o.textContent=".svg-pan-zoom-control { cursor: pointer; fill: black; fill-opacity: 0.333; } .svg-pan-zoom-control:hover { fill-opacity: 0.8; } .svg-pan-zoom-control-background { fill: white; fill-opacity: 0.5; } .svg-pan-zoom-control-background { fill-opacity: 0.8; }",e.appendChild(o);var i=document.createElementNS(n.svgNS,"g");i.setAttribute("id","svg-pan-zoom-controls"),i.setAttribute("transform","translate("+(t.width-70)+" "+(t.height-76)+") scale(0.75)"),i.setAttribute("class","svg-pan-zoom-control"),i.appendChild(this._createZoomIn(t)),i.appendChild(this._createZoomReset(t)),i.appendChild(this._createZoomOut(t)),t.svg.appendChild(i),t.controlIcons=i},_createZoomIn:function(t){var e=document.createElementNS(n.svgNS,"g");e.setAttribute("id","svg-pan-zoom-zoom-in"),e.setAttribute("transform","translate(30.5 5) scale(0.015)"),e.setAttribute("class","svg-pan-zoom-control"),e.addEventListener("click",function(){t.getPublicInstance().zoomIn()},!1),e.addEventListener("touchstart",function(){t.getPublicInstance().zoomIn()},!1);var o=document.createElementNS(n.svgNS,"rect");o.setAttribute("x","0"),o.setAttribute("y","0"),o.setAttribute("width","1500"),o.setAttribute("height","1400"),o.setAttribute("class","svg-pan-zoom-control-background"),e.appendChild(o);var i=document.createElementNS(n.svgNS,"path");return i.setAttribute("d","M1280 576v128q0 26 -19 45t-45 19h-320v320q0 26 -19 45t-45 19h-128q-26 0 -45 -19t-19 -45v-320h-320q-26 0 -45 -19t-19 -45v-128q0 -26 19 -45t45 -19h320v-320q0 -26 19 -45t45 -19h128q26 0 45 19t19 45v320h320q26 0 45 19t19 45zM1536 1120v-960 q0 -119 -84.5 -203.5t-203.5 -84.5h-960q-119 0 -203.5 84.5t-84.5 203.5v960q0 119 84.5 203.5t203.5 84.5h960q119 0 203.5 -84.5t84.5 -203.5z"),i.setAttribute("class","svg-pan-zoom-control-element"),e.appendChild(i),e},_createZoomReset:function(t){var e=document.createElementNS(n.svgNS,"g");e.setAttribute("id","svg-pan-zoom-reset-pan-zoom"),e.setAttribute("transform","translate(5 35) scale(0.4)"),e.setAttribute("class","svg-pan-zoom-control"),e.addEventListener("click",function(){t.getPublicInstance().reset()},!1),e.addEventListener("touchstart",function(){t.getPublicInstance().reset()},!1);var o=document.createElementNS(n.svgNS,"rect");o.setAttribute("x","2"),o.setAttribute("y","2"),o.setAttribute("width","182"),o.setAttribute("height","58"),o.setAttribute("class","svg-pan-zoom-control-background"),e.appendChild(o);var i=document.createElementNS(n.svgNS,"path");i.setAttribute("d","M33.051,20.632c-0.742-0.406-1.854-0.609-3.338-0.609h-7.969v9.281h7.769c1.543,0,2.701-0.188,3.473-0.562c1.365-0.656,2.048-1.953,2.048-3.891C35.032,22.757,34.372,21.351,33.051,20.632z"),i.setAttribute("class","svg-pan-zoom-control-element"),e.appendChild(i);var s=document.createElementNS(n.svgNS,"path");return s.setAttribute("d","M170.231,0.5H15.847C7.102,0.5,0.5,5.708,0.5,11.84v38.861C0.5,56.833,7.102,61.5,15.847,61.5h154.384c8.745,0,15.269-4.667,15.269-10.798V11.84C185.5,5.708,178.976,0.5,170.231,0.5z M42.837,48.569h-7.969c-0.219-0.766-0.375-1.383-0.469-1.852c-0.188-0.969-0.289-1.961-0.305-2.977l-0.047-3.211c-0.03-2.203-0.41-3.672-1.142-4.406c-0.732-0.734-2.103-1.102-4.113-1.102h-7.05v13.547h-7.055V14.022h16.524c2.361,0.047,4.178,0.344,5.45,0.891c1.272,0.547,2.351,1.352,3.234,2.414c0.731,0.875,1.31,1.844,1.737,2.906s0.64,2.273,0.64,3.633c0,1.641-0.414,3.254-1.242,4.84s-2.195,2.707-4.102,3.363c1.594,0.641,2.723,1.551,3.387,2.73s0.996,2.98,0.996,5.402v2.32c0,1.578,0.063,2.648,0.19,3.211c0.19,0.891,0.635,1.547,1.333,1.969V48.569z M75.579,48.569h-26.18V14.022h25.336v6.117H56.454v7.336h16.781v6H56.454v8.883h19.125V48.569z M104.497,46.331c-2.44,2.086-5.887,3.129-10.34,3.129c-4.548,0-8.125-1.027-10.731-3.082s-3.909-4.879-3.909-8.473h6.891c0.224,1.578,0.662,2.758,1.316,3.539c1.196,1.422,3.246,2.133,6.15,2.133c1.739,0,3.151-0.188,4.236-0.562c2.058-0.719,3.087-2.055,3.087-4.008c0-1.141-0.504-2.023-1.512-2.648c-1.008-0.609-2.607-1.148-4.796-1.617l-3.74-0.82c-3.676-0.812-6.201-1.695-7.576-2.648c-2.328-1.594-3.492-4.086-3.492-7.477c0-3.094,1.139-5.664,3.417-7.711s5.623-3.07,10.036-3.07c3.685,0,6.829,0.965,9.431,2.895c2.602,1.93,3.966,4.73,4.093,8.402h-6.938c-0.128-2.078-1.057-3.555-2.787-4.43c-1.154-0.578-2.587-0.867-4.301-0.867c-1.907,0-3.428,0.375-4.565,1.125c-1.138,0.75-1.706,1.797-1.706,3.141c0,1.234,0.561,2.156,1.682,2.766c0.721,0.406,2.25,0.883,4.589,1.43l6.063,1.43c2.657,0.625,4.648,1.461,5.975,2.508c2.059,1.625,3.089,3.977,3.089,7.055C108.157,41.624,106.937,44.245,104.497,46.331z M139.61,48.569h-26.18V14.022h25.336v6.117h-18.281v7.336h16.781v6h-16.781v8.883h19.125V48.569z M170.337,20.14h-10.336v28.43h-7.266V20.14h-10.383v-6.117h27.984V20.14z"),s.setAttribute("class","svg-pan-zoom-control-element"),e.appendChild(s),e},_createZoomOut:function(t){var e=document.createElementNS(n.svgNS,"g");e.setAttribute("id","svg-pan-zoom-zoom-out"),e.setAttribute("transform","translate(30.5 70) scale(0.015)"),e.setAttribute("class","svg-pan-zoom-control"),e.addEventListener("click",function(){t.getPublicInstance().zoomOut()},!1),e.addEventListener("touchstart",function(){t.getPublicInstance().zoomOut()},!1);var o=document.createElementNS(n.svgNS,"rect");o.setAttribute("x","0"),o.setAttribute("y","0"),o.setAttribute("width","1500"),o.setAttribute("height","1400"),o.setAttribute("class","svg-pan-zoom-control-background"),e.appendChild(o);var i=document.createElementNS(n.svgNS,"path");return i.setAttribute("d","M1280 576v128q0 26 -19 45t-45 19h-896q-26 0 -45 -19t-19 -45v-128q0 -26 19 -45t45 -19h896q26 0 45 19t19 45zM1536 1120v-960q0 -119 -84.5 -203.5t-203.5 -84.5h-960q-119 0 -203.5 84.5t-84.5 203.5v960q0 119 84.5 203.5t203.5 84.5h960q119 0 203.5 -84.5 t84.5 -203.5z"),i.setAttribute("class","svg-pan-zoom-control-element"),e.appendChild(i),e},disable:function(t){t.controlIcons&&(t.controlIcons.parentNode.removeChild(t.controlIcons),t.controlIcons=null)}}},{"./svg-utilities":5}],3:[function(t,e,o){var n=t("./svg-utilities"),i=t("./utilities"),s=function(t,e){this.init(t,e)};s.prototype.init=function(t,e){this.viewport=t,this.options=e,this.originalState={zoom:1,x:0,y:0},this.activeState={zoom:1,x:0,y:0},this.updateCTMCached=i.proxy(this.updateCTM,this),this.requestAnimationFrame=i.createRequestAnimationFrame(this.options.refreshRate),this.viewBox={x:0,y:0,width:0,height:0},this.cacheViewBox(),this.processCTM(),this.updateCTM()},s.prototype.cacheViewBox=function(){var t=this.options.svg.getAttribute("viewBox");if(t){var e=t.split(/[\s\,]/).filter(function(t){return t}).map(parseFloat);this.viewBox.x=e[0],this.viewBox.y=e[1],this.viewBox.width=e[2],this.viewBox.height=e[3];var o=Math.min(this.options.width/this.viewBox.width,this.options.height/this.viewBox.height);this.activeState.zoom=o,this.activeState.x=(this.options.width-this.viewBox.width*o)/2,this.activeState.y=(this.options.height-this.viewBox.height*o)/2,this.updateCTMOnNextFrame(),this.options.svg.removeAttribute("viewBox")}else{var n=this.viewport.getBBox();this.viewBox.x=n.x,this.viewBox.y=n.y,this.viewBox.width=n.width,this.viewBox.height=n.height}},s.prototype.recacheViewBox=function(){var t=this.viewport.getBoundingClientRect(),e=t.width/this.getZoom(),o=t.height/this.getZoom();this.viewBox.x=0,this.viewBox.y=0,this.viewBox.width=e,this.viewBox.height=o},s.prototype.getViewBox=function(){return i.extend({},this.viewBox)},s.prototype.processCTM=function(){var t=this.getCTM();if(this.options.fit||this.options.contain){var e;e=this.options.fit?Math.min(this.options.width/this.viewBox.width,this.options.height/this.viewBox.height):Math.max(this.options.width/this.viewBox.width,this.options.height/this.viewBox.height),t.a=e,t.d=e,t.e=-this.viewBox.x*e,t.f=-this.viewBox.y*e}if(this.options.center){var o=.5*(this.options.width-(this.viewBox.width+2*this.viewBox.x)*t.a),n=.5*(this.options.height-(this.viewBox.height+2*this.viewBox.y)*t.a);t.e=o,t.f=n}this.originalState.zoom=t.a,this.originalState.x=t.e,this.originalState.y=t.f,this.setCTM(t)},s.prototype.getOriginalState=function(){return i.extend({},this.originalState)},s.prototype.getState=function(){return i.extend({},this.activeState)},s.prototype.getZoom=function(){return this.activeState.zoom},s.prototype.getRelativeZoom=function(){return this.activeState.zoom/this.originalState.zoom},s.prototype.computeRelativeZoom=function(t){return t/this.originalState.zoom},s.prototype.getPan=function(){return{x:this.activeState.x,y:this.activeState.y}},s.prototype.getCTM=function(){var t=this.options.svg.createSVGMatrix();return t.a=this.activeState.zoom,t.b=0,t.c=0,t.d=this.activeState.zoom,t.e=this.activeState.x,t.f=this.activeState.y,t},s.prototype.setCTM=function(t){var e=this.isZoomDifferent(t),o=this.isPanDifferent(t);if(e||o){if(e&&this.options.beforeZoom(this.getRelativeZoom(),this.computeRelativeZoom(t.a))===!1&&(t.a=t.d=this.activeState.zoom,e=!1),o){var n=this.options.beforePan(this.getPan(),{x:t.e,y:t.f}),s=!1,r=!1;n===!1?(t.e=this.getPan().x,t.f=this.getPan().y,s=r=!0):i.isObject(n)&&(n.x===!1?(t.e=this.getPan().x,s=!0):i.isNumber(n.x)&&(t.e=n.x),n.y===!1?(t.f=this.getPan().y,r=!0):i.isNumber(n.y)&&(t.f=n.y)),s&&r&&(o=!1)}(e||o)&&(this.updateCache(t),this.updateCTMOnNextFrame(),e&&this.options.onZoom(this.getRelativeZoom()),o&&this.options.onPan(this.getPan()))}},s.prototype.isZoomDifferent=function(t){return this.activeState.zoom!==t.a},s.prototype.isPanDifferent=function(t){return this.activeState.x!==t.e||this.activeState.y!==t.f},s.prototype.updateCache=function(t){this.activeState.zoom=t.a,this.activeState.x=t.e,this.activeState.y=t.f},s.prototype.pendingUpdate=!1,s.prototype.updateCTMOnNextFrame=function(){this.pendingUpdate||(this.pendingUpdate=!0,this.requestAnimationFrame.call(window,this.updateCTMCached))},s.prototype.updateCTM=function(){n.setCTM(this.viewport,this.getCTM(),this.defs),this.pendingUpdate=!1},e.exports=function(t,e){return new s(t,e)}},{"./svg-utilities":5,"./utilities":7}],4:[function(t,e,o){var n=t("./uniwheel"),i=t("./control-icons"),s=t("./utilities"),r=t("./svg-utilities"),a=t("./shadow-viewport"),l=function(t,e){this.init(t,e)},u={viewportSelector:".svg-pan-zoom_viewport",panEnabled:!0,controlIconsEnabled:!1,zoomEnabled:!0,dblClickZoomEnabled:!0,mouseWheelZoomEnabled:!0,preventMouseEventsDefault:!0,zoomScaleSensitivity:.1,minZoom:.5,maxZoom:10,fit:!0,contain:!1,center:!0,refreshRate:"auto",beforeZoom:null,onZoom:null,beforePan:null,onPan:null,customEventsHandler:null,eventsListenerElement:null};l.prototype.init=function(t,e){var o=this;this.svg=t,this.defs=t.querySelector("defs"),r.setupSvgAttributes(this.svg),this.options=s.extend(s.extend({},u),e),this.state="none";var n=r.getBoundingClientRectNormalized(t);this.width=n.width,this.height=n.height,this.viewport=a(r.getOrCreateViewport(this.svg,this.options.viewportSelector),{svg:this.svg,width:this.width,height:this.height,fit:this.options.fit,contain:this.options.contain,center:this.options.center,refreshRate:this.options.refreshRate,beforeZoom:function(t,e){return o.viewport&&o.options.beforeZoom?o.options.beforeZoom(t,e):void 0},onZoom:function(t){return o.viewport&&o.options.onZoom?o.options.onZoom(t):void 0},beforePan:function(t,e){return o.viewport&&o.options.beforePan?o.options.beforePan(t,e):void 0},onPan:function(t){return o.viewport&&o.options.onPan?o.options.onPan(t):void 0}});var l=this.getPublicInstance();l.setBeforeZoom(this.options.beforeZoom),l.setOnZoom(this.options.onZoom),l.setBeforePan(this.options.beforePan),l.setOnPan(this.options.onPan),this.options.controlIconsEnabled&&i.enable(this),this.lastMouseWheelEventTime=Date.now(),this.setupHandlers()},l.prototype.setupHandlers=function(){var t=this,e=null;if(this.eventListeners={mousedown:function(e){return t.handleMouseDown(e,null)},touchstart:function(o){var n=t.handleMouseDown(o,e);return e=o,n},mouseup:function(e){return t.handleMouseUp(e)},touchend:function(e){return t.handleMouseUp(e)},mousemove:function(e){return t.handleMouseMove(e)},touchmove:function(e){return t.handleMouseMove(e)},mouseleave:function(e){return t.handleMouseUp(e)},touchleave:function(e){return t.handleMouseUp(e)},touchcancel:function(e){return t.handleMouseUp(e)}},null!=this.options.customEventsHandler){this.options.customEventsHandler.init({svgElement:this.svg,eventsListenerElement:this.options.eventsListenerElement,instance:this.getPublicInstance()});var o=this.options.customEventsHandler.haltEventListeners;if(o&&o.length)for(var n=o.length-1;n>=0;n--)this.eventListeners.hasOwnProperty(o[n])&&delete this.eventListeners[o[n]]}for(var i in this.eventListeners)(this.options.eventsListenerElement||this.svg).addEventListener(i,this.eventListeners[i],!1);this.options.mouseWheelZoomEnabled&&(this.options.mouseWheelZoomEnabled=!1,this.enableMouseWheelZoom())},l.prototype.enableMouseWheelZoom=function(){if(!this.options.mouseWheelZoomEnabled){var t=this;this.wheelListener=function(e){return t.handleMouseWheel(e)},n.on(this.options.eventsListenerElement||this.svg,this.wheelListener,!1),this.options.mouseWheelZoomEnabled=!0}},l.prototype.disableMouseWheelZoom=function(){this.options.mouseWheelZoomEnabled&&(n.off(this.options.eventsListenerElement||this.svg,this.wheelListener,!1),this.options.mouseWheelZoomEnabled=!1)},l.prototype.handleMouseWheel=function(t){if(this.options.zoomEnabled&&"none"===this.state){this.options.preventMouseEventsDefault&&(t.preventDefault?t.preventDefault():t.returnValue=!1);var e=t.deltaY||1,o=Date.now()-this.lastMouseWheelEventTime,n=3+Math.max(0,30-o);this.lastMouseWheelEventTime=Date.now(),"deltaMode"in t&&0===t.deltaMode&&t.wheelDelta&&(e=0===t.deltaY?0:Math.abs(t.wheelDelta)/t.deltaY),e=e>-.3&&.3>e?e:(e>0?1:-1)*Math.log(Math.abs(e)+10)/n;var i=this.svg.getScreenCTM().inverse(),s=r.getEventPoint(t,this.svg).matrixTransform(i),a=Math.pow(1+this.options.zoomScaleSensitivity,-1*e);this.zoomAtPoint(a,s)}},l.prototype.zoomAtPoint=function(t,e,o){var n=this.viewport.getOriginalState();o?(t=Math.max(this.options.minZoom*n.zoom,Math.min(this.options.maxZoom*n.zoom,t)),t/=this.getZoom()):this.getZoom()*t<this.options.minZoom*n.zoom?t=this.options.minZoom*n.zoom/this.getZoom():this.getZoom()*t>this.options.maxZoom*n.zoom&&(t=this.options.maxZoom*n.zoom/this.getZoom());var i=this.viewport.getCTM(),s=e.matrixTransform(i.inverse()),r=this.svg.createSVGMatrix().translate(s.x,s.y).scale(t).translate(-s.x,-s.y),a=i.multiply(r);a.a!==i.a&&this.viewport.setCTM(a)},l.prototype.zoom=function(t,e){this.zoomAtPoint(t,r.getSvgCenterPoint(this.svg,this.width,this.height),e)},l.prototype.publicZoom=function(t,e){e&&(t=this.computeFromRelativeZoom(t)),this.zoom(t,e)},l.prototype.publicZoomAtPoint=function(t,e,o){if(o&&(t=this.computeFromRelativeZoom(t)),"SVGPoint"!==s.getType(e)){if(!("x"in e&&"y"in e))throw new Error("Given point is invalid");e=r.createSVGPoint(this.svg,e.x,e.y)}this.zoomAtPoint(t,e,o)},l.prototype.getZoom=function(){return this.viewport.getZoom()},l.prototype.getRelativeZoom=function(){return this.viewport.getRelativeZoom()},l.prototype.computeFromRelativeZoom=function(t){return t*this.viewport.getOriginalState().zoom},l.prototype.resetZoom=function(){var t=this.viewport.getOriginalState();this.zoom(t.zoom,!0)},l.prototype.resetPan=function(){this.pan(this.viewport.getOriginalState())},l.prototype.reset=function(){this.resetZoom(),this.resetPan()},l.prototype.handleDblClick=function(t){if(this.options.preventMouseEventsDefault&&(t.preventDefault?t.preventDefault():t.returnValue=!1),this.options.controlIconsEnabled){var e=t.target.getAttribute("class")||"";if(e.indexOf("svg-pan-zoom-control")>-1)return!1}var o;o=t.shiftKey?1/(2*(1+this.options.zoomScaleSensitivity)):2*(1+this.options.zoomScaleSensitivity);var n=r.getEventPoint(t,this.svg).matrixTransform(this.svg.getScreenCTM().inverse());this.zoomAtPoint(o,n)},l.prototype.handleMouseDown=function(t,e){this.options.preventMouseEventsDefault&&(t.preventDefault?t.preventDefault():t.returnValue=!1),s.mouseAndTouchNormalize(t,this.svg),this.options.dblClickZoomEnabled&&s.isDblClick(t,e)?this.handleDblClick(t):(this.state="pan",this.firstEventCTM=this.viewport.getCTM(),this.stateOrigin=r.getEventPoint(t,this.svg).matrixTransform(this.firstEventCTM.inverse()))},l.prototype.handleMouseMove=function(t){if(this.options.preventMouseEventsDefault&&(t.preventDefault?t.preventDefault():t.returnValue=!1),"pan"===this.state&&this.options.panEnabled){var e=r.getEventPoint(t,this.svg).matrixTransform(this.firstEventCTM.inverse()),o=this.firstEventCTM.translate(e.x-this.stateOrigin.x,e.y-this.stateOrigin.y);this.viewport.setCTM(o)}},l.prototype.handleMouseUp=function(t){this.options.preventMouseEventsDefault&&(t.preventDefault?t.preventDefault():t.returnValue=!1),"pan"===this.state&&(this.state="none")},l.prototype.fit=function(){var t=this.viewport.getViewBox(),e=Math.min(this.width/t.width,this.height/t.height);this.zoom(e,!0)},l.prototype.contain=function(){var t=this.viewport.getViewBox(),e=Math.max(this.width/t.width,this.height/t.height);this.zoom(e,!0)},l.prototype.center=function(){var t=this.viewport.getViewBox(),e=.5*(this.width-(t.width+2*t.x)*this.getZoom()),o=.5*(this.height-(t.height+2*t.y)*this.getZoom());this.getPublicInstance().pan({x:e,y:o})},l.prototype.updateBBox=function(){this.viewport.recacheViewBox()},l.prototype.pan=function(t){var e=this.viewport.getCTM();e.e=t.x,e.f=t.y,this.viewport.setCTM(e)},l.prototype.panBy=function(t){var e=this.viewport.getCTM();e.e+=t.x,e.f+=t.y,this.viewport.setCTM(e)},l.prototype.getPan=function(){var t=this.viewport.getState();return{x:t.x,y:t.y}},l.prototype.resize=function(){var t=r.getBoundingClientRectNormalized(this.svg);this.width=t.width,this.height=t.height,this.options.controlIconsEnabled&&(this.getPublicInstance().disableControlIcons(),this.getPublicInstance().enableControlIcons())},l.prototype.destroy=function(){var t=this;this.beforeZoom=null,this.onZoom=null,this.beforePan=null,this.onPan=null,null!=this.options.customEventsHandler&&this.options.customEventsHandler.destroy({svgElement:this.svg,eventsListenerElement:this.options.eventsListenerElement,instance:this.getPublicInstance()});for(var e in this.eventListeners)(this.options.eventsListenerElement||this.svg).removeEventListener(e,this.eventListeners[e],!1);this.disableMouseWheelZoom(),this.getPublicInstance().disableControlIcons(),this.reset(),h=h.filter(function(e){return e.svg!==t.svg}),delete this.options,delete this.publicInstance,delete this.pi,this.getPublicInstance=function(){return null}},l.prototype.getPublicInstance=function(){var t=this;return this.publicInstance||(this.publicInstance=this.pi={enablePan:function(){return t.options.panEnabled=!0,t.pi},disablePan:function(){return t.options.panEnabled=!1,t.pi},isPanEnabled:function(){return!!t.options.panEnabled},pan:function(e){return t.pan(e),t.pi},panBy:function(e){return t.panBy(e),t.pi},getPan:function(){return t.getPan()},setBeforePan:function(e){return t.options.beforePan=null===e?null:s.proxy(e,t.publicInstance),t.pi},setOnPan:function(e){return t.options.onPan=null===e?null:s.proxy(e,t.publicInstance),t.pi},enableZoom:function(){return t.options.zoomEnabled=!0,t.pi},disableZoom:function(){return t.options.zoomEnabled=!1,t.pi},isZoomEnabled:function(){return!!t.options.zoomEnabled},enableControlIcons:function(){return t.options.controlIconsEnabled||(t.options.controlIconsEnabled=!0,i.enable(t)),t.pi},disableControlIcons:function(){return t.options.controlIconsEnabled&&(t.options.controlIconsEnabled=!1,i.disable(t)),t.pi},isControlIconsEnabled:function(){return!!t.options.controlIconsEnabled},enableDblClickZoom:function(){return t.options.dblClickZoomEnabled=!0,t.pi},disableDblClickZoom:function(){return t.options.dblClickZoomEnabled=!1,t.pi},isDblClickZoomEnabled:function(){return!!t.options.dblClickZoomEnabled},enableMouseWheelZoom:function(){return t.enableMouseWheelZoom(),t.pi},disableMouseWheelZoom:function(){return t.disableMouseWheelZoom(),t.pi},isMouseWheelZoomEnabled:function(){return!!t.options.mouseWheelZoomEnabled},setZoomScaleSensitivity:function(e){return t.options.zoomScaleSensitivity=e,t.pi},setMinZoom:function(e){return t.options.minZoom=e,t.pi},setMaxZoom:function(e){return t.options.maxZoom=e,t.pi},setBeforeZoom:function(e){return t.options.beforeZoom=null===e?null:s.proxy(e,t.publicInstance),t.pi},setOnZoom:function(e){return t.options.onZoom=null===e?null:s.proxy(e,t.publicInstance),t.pi},zoom:function(e){return t.publicZoom(e,!0),t.pi},zoomBy:function(e){return t.publicZoom(e,!1),t.pi},zoomAtPoint:function(e,o){return t.publicZoomAtPoint(e,o,!0),t.pi},zoomAtPointBy:function(e,o){return t.publicZoomAtPoint(e,o,!1),t.pi},zoomIn:function(){return this.zoomBy(1+t.options.zoomScaleSensitivity),t.pi},zoomOut:function(){return this.zoomBy(1/(1+t.options.zoomScaleSensitivity)),t.pi},getZoom:function(){return t.getRelativeZoom()},resetZoom:function(){return t.resetZoom(),t.pi},resetPan:function(){return t.resetPan(),t.pi},reset:function(){return t.reset(),t.pi},fit:function(){return t.fit(),t.pi},contain:function(){return t.contain(),t.pi},center:function(){return t.center(),t.pi},updateBBox:function(){return t.updateBBox(),t.pi},resize:function(){return t.resize(),t.pi},getSizes:function(){return{width:t.width,height:t.height,realZoom:t.getZoom(),viewBox:t.viewport.getViewBox()}},destroy:function(){return t.destroy(),t.pi}}),this.publicInstance};var h=[],c=function(t,e){var o=s.getSvg(t);if(null===o)return null;for(var n=h.length-1;n>=0;n--)if(h[n].svg===o)return h[n].instance.getPublicInstance();return h.push({svg:o,instance:new l(o,e)}),h[h.length-1].instance.getPublicInstance()};e.exports=c},{"./control-icons":2,"./shadow-viewport":3,"./svg-utilities":5,"./uniwheel":6,"./utilities":7}],5:[function(t,e,o){var n=t("./utilities"),i="unknown";document.documentMode&&(i="ie"),e.exports={svgNS:"http://www.w3.org/2000/svg",xmlNS:"http://www.w3.org/XML/1998/namespace",xmlnsNS:"http://www.w3.org/2000/xmlns/",xlinkNS:"http://www.w3.org/1999/xlink",evNS:"http://www.w3.org/2001/xml-events",getBoundingClientRectNormalized:function(t){if(t.clientWidth&&t.clientHeight)return{width:t.clientWidth,height:t.clientHeight};if(t.getBoundingClientRect())return t.getBoundingClientRect();throw new Error("Cannot get BoundingClientRect for SVG.")},getOrCreateViewport:function(t,e){var o=null;if(o=n.isElement(e)?e:t.querySelector(e),!o){var i=Array.prototype.slice.call(t.childNodes||t.children).filter(function(t){return"defs"!==t.nodeName&&"#text"!==t.nodeName});1===i.length&&"g"===i[0].nodeName&&null===i[0].getAttribute("transform")&&(o=i[0])}if(!o){var s="viewport-"+(new Date).toISOString().replace(/\D/g,"");o=document.createElementNS(this.svgNS,"g"),o.setAttribute("id",s);var r=t.childNodes||t.children;if(r&&r.length>0)for(var a=r.length;a>0;a--)"defs"!==r[r.length-a].nodeName&&o.appendChild(r[r.length-a]);t.appendChild(o)}var l=[];return o.getAttribute("class")&&(l=o.getAttribute("class").split(" ")),~l.indexOf("svg-pan-zoom_viewport")||(l.push("svg-pan-zoom_viewport"),o.setAttribute("class",l.join(" "))),o},setupSvgAttributes:function(t){if(t.setAttribute("xmlns",this.svgNS),t.setAttributeNS(this.xmlnsNS,"xmlns:xlink",this.xlinkNS),t.setAttributeNS(this.xmlnsNS,"xmlns:ev",this.evNS),null!==t.parentNode){var e=t.getAttribute("style")||"";-1===e.toLowerCase().indexOf("overflow")&&t.setAttribute("style","overflow: hidden; "+e)}},internetExplorerRedisplayInterval:300,refreshDefsGlobal:n.throttle(function(){for(var t=document.querySelectorAll("defs"),e=t.length,o=0;e>o;o++){var n=t[o];n.parentNode.insertBefore(n,n)}},this.internetExplorerRedisplayInterval),setCTM:function(t,e,o){var n=this,s="matrix("+e.a+","+e.b+","+e.c+","+e.d+","+e.e+","+e.f+")";t.setAttributeNS(null,"transform",s),"ie"===i&&o&&(o.parentNode.insertBefore(o,o),window.setTimeout(function(){n.refreshDefsGlobal()},n.internetExplorerRedisplayInterval))},getEventPoint:function(t,e){var o=e.createSVGPoint();return n.mouseAndTouchNormalize(t,e),o.x=t.clientX,o.y=t.clientY,o},getSvgCenterPoint:function(t,e,o){return this.createSVGPoint(t,e/2,o/2)},createSVGPoint:function(t,e,o){var n=t.createSVGPoint();return n.x=e,n.y=o,n}}},{"./utilities":7}],6:[function(t,e,o){e.exports=function(){function t(t,e,o){var n=function(t){!t&&(t=window.event);var o={originalEvent:t,target:t.target||t.srcElement,type:"wheel",deltaMode:"MozMousePixelScroll"==t.type?0:1,deltaX:0,delatZ:0,preventDefault:function(){t.preventDefault?t.preventDefault():t.returnValue=!1}};return"mousewheel"==u?(o.deltaY=-1/40*t.wheelDelta,t.wheelDeltaX&&(o.deltaX=-1/40*t.wheelDeltaX)):o.deltaY=t.detail,e(o)};return c.push({element:t,fn:n,capture:o}),n}function e(t,e){for(var o=0;o<c.length;o++)if(c[o].element===t&&c[o].capture===e)return c[o].fn;return function(){}}function o(t,e){for(var o=0;o<c.length;o++)if(c[o].element===t&&c[o].capture===e)return c.splice(o,1)}function n(e,o,n,i){var s;s="wheel"===u?n:t(e,n,i),e[a](h+o,s,i||!1)}function i(t,n,i,s){"wheel"===u?cb=i:cb=e(t,s),t[l](h+n,cb,s||!1),o(t,s)}function s(t,e,o){n(t,u,e,o),"DOMMouseScroll"==u&&n(t,"MozMousePixelScroll",e,o)}function r(t,e,o){i(t,u,e,o),"DOMMouseScroll"==u&&i(t,"MozMousePixelScroll",e,o)}var a,l,u,h="",c=[];return window.addEventListener?(a="addEventListener",l="removeEventListener"):(a="attachEvent",l="detachEvent",h="on"),u="onwheel"in document.createElement("div")?"wheel":void 0!==document.onmousewheel?"mousewheel":"DOMMouseScroll",{on:s,off:r}}()},{}],7:[function(t,e,o){function n(t){return function(e){window.setTimeout(e,t)}}e.exports={extend:function(t,e){t=t||{};for(var o in e)this.isObject(e[o])?t[o]=this.extend(t[o],e[o]):t[o]=e[o];return t},isElement:function(t){return t instanceof HTMLElement||t instanceof SVGElement||t instanceof SVGSVGElement||t&&"object"==typeof t&&null!==t&&1===t.nodeType&&"string"==typeof t.nodeName},isObject:function(t){return"[object Object]"===Object.prototype.toString.call(t)},isNumber:function(t){return!isNaN(parseFloat(t))&&isFinite(t)},getSvg:function(t){var e,o;if(this.isElement(t))e=t;else{if(!("string"==typeof t||t instanceof String))throw new Error("Provided selector is not an HTML object nor String");if(e=document.querySelector(t),!e)throw new Error("Provided selector did not find any elements. Selector: "+t)}if("svg"===e.tagName.toLowerCase())o=e;else if("object"===e.tagName.toLowerCase())o=e.contentDocument.documentElement;else{if("embed"!==e.tagName.toLowerCase())throw"img"===e.tagName.toLowerCase()?new Error('Cannot script an SVG in an "img" element. Please use an "object" element or an in-line SVG.'):new Error("Cannot get SVG.");o=e.getSVGDocument().documentElement}return o},proxy:function(t,e){return function(){return t.apply(e,arguments)}},getType:function(t){return Object.prototype.toString.apply(t).replace(/^\[object\s/,"").replace(/\]$/,"")},mouseAndTouchNormalize:function(t,e){if(void 0===t.clientX||null===t.clientX)if(t.clientX=0,t.clientY=0,void 0!==t.changedTouches&&t.changedTouches.length){if(void 0!==t.changedTouches[0].clientX)t.clientX=t.changedTouches[0].clientX,t.clientY=t.changedTouches[0].clientY;else if(void 0!==t.changedTouches[0].pageX){var o=e.getBoundingClientRect();t.clientX=t.changedTouches[0].pageX-o.left,t.clientY=t.changedTouches[0].pageY-o.top}}else void 0!==t.originalEvent&&void 0!==t.originalEvent.clientX&&(t.clientX=t.originalEvent.clientX,t.clientY=t.originalEvent.clientY)},isDblClick:function(t,e){if(2===t.detail)return!0;if(void 0!==e&&null!==e){var o=t.timeStamp-e.timeStamp,n=Math.sqrt(Math.pow(t.clientX-e.clientX,2)+Math.pow(t.clientY-e.clientY,2));return 250>o&&10>n}return!1},now:Date.now||function(){return(new Date).getTime()},throttle:function(t,e,o){var n,i,s,r=this,a=null,l=0;o||(o={});var u=function(){l=o.leading===!1?0:r.now(),a=null,s=t.apply(n,i),a||(n=i=null)};return function(){var h=r.now();l||o.leading!==!1||(l=h);var c=e-(h-l);return n=this,i=arguments,0>=c||c>e?(clearTimeout(a),a=null,l=h,s=t.apply(n,i),a||(n=i=null)):a||o.trailing===!1||(a=setTimeout(u,c)),s}},createRequestAnimationFrame:function(t){var e=null;return"auto"!==t&&60>t&&t>1&&(e=Math.floor(1e3/t)),null===e?window.requestAnimationFrame||n(33):n(e)}}},{}]},{},[1]);
</script>
</body>
<script>
  function resize_container(){
  var w = window,
    d = document,
    e = d.documentElement,
    g = d.getElementsByTagName('body')[0],
    x = w.innerWidth || e.clientWidth || g.clientWidth,
    y = w.innerHeight|| e.clientHeight|| g.clientHeight;
    document.getElementById("container").style.width = x-20;
    document.getElementById("container").style.height = y-20;
  }
  function resize_pan(){
    panZoom.resize();
    panZoom.fit();
    panZoom.center();
    document.getElementById("container").style.opacity = 1;
  }
  resize_container();

  window.onload = function() {
    //alert('loaded')
    window.panZoom = svgPanZoom('#preview', {
      zoomEnabled: true,
      controlIconsEnabled: true,
      fit: true,
      center: true,
    });
    resize_pan();
    //alert('window.panZoom')
  };
  window.onresize = function(){
      resize_container();
      resize_pan();
  }
</script>
</html>
''')

def group(t, n):
    return zip(*[t[i::n] for i in range(n)])


def mm2px(dpi, val):
    return int(round(1.0 * val * dpi * 0.0393701))


def hex_color(rgb_tuple):
    hexcolor = '#%02x%02x%02x' % tuple([int(x) for x in rgb_tuple])
    return hexcolor


def polygon_topath(data):
    polygons = data[4:]
    color = data[1:4]
    path = ['<path style="stroke:%s; fill:none; stroke-width: 3;" ' % hex_color(color), 'd="M']
    for p in group(polygons, 2):
        path.append("%s,%s " % tuple(p))
    path.append('" />')
    return "".join(path)


def get_base64_img(tsf_buff):
    encoded_string = None
    m = bmp_re.search(tsf_buff)
    if m:
        _bmp_file, _bmp_filename = tempfile.mkstemp(suffix=".bmp")
        os.write(_bmp_file, "BM")
        os.write(_bmp_file, m.group(2))
        os.close(_bmp_file)
        _jpg_file, _jpg_filename = tempfile.mkstemp(suffix=".jpg")
        os.close(_jpg_file)
        # convert_command(_bmp_filename, "-resize", '"1920x1080>"', "-flip", _jpg_filename)
        convert_command(_bmp_filename, "-flip", _jpg_filename)
        with open(_jpg_filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
        os.remove(_bmp_filename)
        os.remove(_jpg_filename)
        return encoded_string


def parse_headers(tsf_file):
    try:
        with open(tsf_file, "r") as f:
            tsf_buff = f.read()

            headers = {}
            for k in headers_re:
                if(headers_re[k].search(tsf_buff)):
                    headers[k] = headers_transfo[k](headers_re[k].search(tsf_buff).groups())

            headers['px_width'] = mm2px(headers['Resolution'], headers['Size']['width'])
            headers['px_height'] = mm2px(headers['Resolution'], headers['Size']['height'])
            headers['bmp'] = False

            if(bmp_re.search(tsf_buff)):
                headers['bmp'] = True

            colors = set()
            for p in polygones_re.findall(tsf_buff):
                colors.add(hex_color(p.split(';')[1:4]))

            headers['cut'] = list(colors)

            headers['valid'] = True
            return headers
    except Exception:
        logging.exception("Error loading headers for %s" % tsf_file)
        return {"valid": False}


def parse_headers2(tsf_file):
    try:
        with open(tsf_file, "r") as _file:
            headers = {
                'ProcessMode': None,
                'Size': {'width': 0, 'height': 0},
                'MaterialGroup': None,
                'MaterialName': None,
                'JobName': None,
                'JobNumber': 0,
                'Resolution': 300,
                'LayerParameter': {'layers': 1, 'adjustment': 0},
                'StampShoulder': None,
                'Cutline': [],
            }
            headers['bmp'] = False
            colors = set()
            for line in _file:
                for k in headers_re:
                    found = headers_re[k].search(line)
                    if(found):
                        headers[k] = headers_transfo[k](found.groups())
                        break

                if line.find('<BegGroup: Bitmap>') > -1:
                    headers['bmp'] = True

                for p in polygones_re.findall(line):
                    colors.add(hex_color(p.split(';')[1:4]))

            headers['px_width'] = mm2px(headers['Resolution'], headers['Size']['width'])
            headers['px_height'] = mm2px(headers['Resolution'], headers['Size']['height'])
            headers['valid'] = True

            headers['cut'] = [k for k in TROTEC_COLORS if k in colors]
            return headers
    except Exception:
        logging.exception("Error loading headers for %s" % tsf_file)
        return {"valid": False}

# deprecated won't work anymore


def extract_preview(tsf_file, headers, svg_path):
    engrave_img = None
    try:
        with open(tsf_file, "r") as f:
            tsf_buff = f.read()
            engrave_img = get_base64_img(tsf_buff)

    except Exception:
        logging.exception("Error extracting preview for %s" % tsf_file)

    with open(svg_path, "w+") as svg_file:
        svg_file.write(extract_svg(tsf_file, headers, engrave_img))


def extract_preview_as_html(tsf_file, headers, html_path, export_time=None):
    engrave_img = None
    try:
        with open(tsf_file, "r") as f:
            tsf_buff = f.read()
            engrave_img = get_base64_img(tsf_buff)
    except Exception:
        logging.exception("Error extracting preview for %s" % tsf_file)

    file_size = path.getsize(tsf_file)

    with open(html_path, "w+") as html_path_file:
        engraving = "Aucune gravure"
        if(headers.get('bmp')):
            if headers.get('ProcessMode') == "Standard":
                engraving = "Standard"
            elif headers.get('ProcessMode') == "Relief":
                engraving = "Relief"
            elif headers.get('ProcessMode') == "Layer":
                engraving = "%s Couches <em>(ajustement : %s)</em>" % (headers.get('LayerParameter',{}).get('layers'), headers.get('LayerParameter', {}).get('adjustment'))
            elif headers.get('ProcessMode') == "Stamp":
                engraving = "Tampon <em>(%s)</em>" % StampShoulders.get(headers.get('StampShoulder'))

        colors = headers.get('cut', [])
        cut_str = [" %s couleur" % len(colors)]
        if len(colors) > 1:
            cut_str.append("s")

        if len(colors) > 0:
            cut_str.append(" : ")
            for c in colors:
                cut_str.append("<span style='color:%s;'>&#9608;</span> " % c)


        html_path_file.write(HTML_TEMPLATE.safe_substitute({
            'svg': extract_svg(tsf_file, headers, engrave_img),
            'jobname': headers.get("JobName"),
            'size': "%sx%s mm" % (int(math.ceil(headers.get('Size').get('width'))), int(math.ceil(headers.get('Size').get('height')))),
            'colors': '<li><strong>D&eacute;coupe : </strong> %s </li>' % "".join(cut_str),
            'export_time': '<div style="align:center;"><em>Export effectu&eacute; en %ss</em></div>' % export_time if export_time is not None else '',
            'engraving': engraving,
            'headers': "%s" % headers,
            'resolution': "%sDPI" % headers.get('Resolution'),
            'material_group': headers.get('MaterialGroup'),
            'material_name': headers.get('MaterialName'),
            'resolution': "%sDPI" % headers.get('Resolution'),
            'file_size': str_weight(file_size)
        }))


def extract_svg(tsf_file, headers, engrave_img=None):
    with open(tsf_file, "r") as f:
        tsf_buff = f.read()
        svg = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" id="preview"  viewBox="0 0 %s %s" >' % (headers.get("px_width"), headers.get("px_height"))]
        svg.append('<rect style="fill:#FFFFFF;stroke:non;marker:none;"')
        svg.append('width="%s"' % headers.get("px_width"))
        svg.append('height="%s"' % headers.get("px_height"))
        svg.append('x="0"')
        svg.append('y="0" />')

        if(engrave_img):
            # with open(jpg_path, "rb") as img:
                # svg.append('<image x="0" y="0" width="%s" height="%s" xlink:href="data:image/jpg;base64,%s" />' % (headers.get("px_width"), headers.get("px_height"), img.read().encode("base64").replace('\n', '')))
            svg.append('<image x="0" y="0" width="%s" height="%s" xlink:href="data:image/jpg;base64,%s" />' % (headers.get("px_width"), headers.get("px_height"), engrave_img))
        for p in polygones_re.findall(tsf_buff):
            svg.append(polygon_topath(p.split(';')))
        svg.append("</svg>")
    return "\n".join(svg)


def mkdir(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def str_weight(weight):
    i = 0
    while weight > 1024:
        weight = 1.0 * weight / 1024
        i += 1
    # logging.debug(weight)
    return "%0.1f%s" % (weight, ("o", "Ko", "Mo", "Go", "To")[i])


class TsfFilePreviewer:

    def __init__(self, full_path,  export_time=None):
        if not path.isfile(full_path):
            raise Exception("%s is not a file" % full_path)

        self.full_path = full_path
        self.export_time = export_time

        self.directory, self.filename = path.split(self.full_path)
        self.name = self.filename.replace(".tsf", "")
        self._checksum = None
        self._headers = None
        self.creation_date = datetime.fromtimestamp(path.getctime(full_path))
        self.modification_date = datetime.fromtimestamp(path.getmtime(full_path))
        self.size = path.getsize(full_path)

    def checksum_md5(self):
        if not self._checksum:
            md5 = hashlib.md5()
            with open(self.full_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            self._checksum = md5.hexdigest()
        return self._checksum

    def to_dict(self):
        return {
            'directory': self.directory,
            'filename': self.filename,
            'checksum': self.checksum_md5(),
            'headers': self.headers(),
            'date': self.creation_date.isoformat(),
            'weight': self.size,
            'sweight': str_weight(self.size)
        }

    def headers(self):
        if self._headers is None:
            self._headers = parse_headers2(self.full_path)
        return self._headers

    def generate_preview(self, preview_svg):
        extract_preview(self.full_path, self.headers(), preview_svg)
        return preview_svg

    def generate_html_preview(self, preview_svg):
        extract_preview_as_html(self.full_path, self.headers(), preview_svg, export_time=self.export_time)
        return preview_svg

    def show_preview(self):
        _preview_file, _preview = tempfile.mkstemp(".html")
        os.close(_preview_file)
        self.generate_html_preview(_preview)
        try:
            webbrowser.get('firefox').open(_preview)
        except:
            try:
                webbrowser.get('chrome').open(_preview)
            except:
                webbrowser.open(_preview, new=1)
#        os.remove(_preview)


if __name__ == "__main__":
    TsfFilePreviewer(sys.argv[1]).show_preview()
