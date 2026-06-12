# Card templates — Chinese Geography

Paste each Front/Back into Anki › Tools › Manage Note Types › *ChinaProvinces* › Cards. Styling lives in `styling.css`.


## Card 1 — maps

**Front**

```html
{{Map}}
```

**Back**

```html
{{FrontSide}}

<hr id=answer>

<div class="english">{{Name}}</div><div class="idblock"><div class="idline"><span class="hanzi simp-han">{{Name in simplified Chinese}}</span><span class="trad"> <span class="tlabel">trad</span> <span class="trad-han">{{Name in traditional Chinese}}</span></span></div><div class="pinyin">{{Name in pinyin}}</div><div class="audio">{{Pronunciation}}</div></div>{{#Capital in simplified Chinese}}<div class="capblock"><div class="label cap">capital</div><div class="hanzi sm">{{Capital in simplified Chinese}}</div><div class="pinyin">{{Capital in pinyin}}</div><div class="rom">{{Capital}}</div></div>{{/Capital in simplified Chinese}}
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```


## Card 2 — locate

**Front**

```html
<div class="prompt">Where is</div><div class="english">{{Name}}</div><div class="hanzi sm">{{Name in simplified Chinese}}</div><div class="pinyin">{{Name in pinyin}}</div><img src="_China_base.png">
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```

**Back**

```html
<div class="english">{{Name}}</div><div class="hanzi sm">{{Name in simplified Chinese}}</div><div class="pinyin">{{Name in pinyin}}</div><hr id=answer>{{Map}}
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```


## Card 3 — capitals

**Front**

```html
{{#Capital in simplified Chinese}}<div class="prompt">Capital of</div><div class="english">{{Name}}</div><div class="hanzi sm">{{Name in simplified Chinese}}</div><div class="pinyin">{{Name in pinyin}}</div>{{/Capital in simplified Chinese}}
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```

**Back**

```html
{{FrontSide}}

<hr id=answer>

<div class="label cap">capital</div><div class="hanzi">{{Capital in simplified Chinese}}</div><div class="pinyin">{{Capital in pinyin}}</div><div class="rom">{{Capital}}</div><div class="audio">{{Capital audio}}</div>
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```


## Card 4 — capital -> province

**Front**

```html
{{#Capital in simplified Chinese}}<div class="hanzi hanzi-lg">{{Capital in simplified Chinese}}</div><div class="pinyin">{{Capital in pinyin}}</div><div class="rom">{{Capital}}</div><div class="audio">{{Capital audio}}</div><div class="prompt">&hellip; is the capital of which province?</div>{{/Capital in simplified Chinese}}
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```

**Back**

```html
{{FrontSide}}

<hr id=answer>

<div class="english">{{Name}}</div><div class="idblock"><div class="idline"><span class="hanzi simp-han">{{Name in simplified Chinese}}</span><span class="trad"> <span class="tlabel">trad</span> <span class="trad-han">{{Name in traditional Chinese}}</span></span></div><div class="pinyin">{{Name in pinyin}}</div><div class="audio">{{Pronunciation}}</div></div>
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```


## Card 5 — reading

**Front**

```html
<div class="prompt">Which province / municipality?</div><div class="hanzi hanzi-lg">{{Name in simplified Chinese}}</div>
```

**Back**

```html
{{FrontSide}}

<hr id=answer>

<div class="english">{{Name}}</div><div class="idblock"><div class="pinyin">{{Name in pinyin}}</div><div class="audio">{{Pronunciation}}</div><div class="idline"><span class="simp-han" hidden>{{Name in simplified Chinese}}</span><span class="trad"><span class="tlabel">trad</span> <span class="trad-han">{{Name in traditional Chinese}}</span></span></div></div>{{#Capital in simplified Chinese}}<div class="capblock"><div class="label cap">capital</div><div class="hanzi sm">{{Capital in simplified Chinese}}</div><div class="pinyin">{{Capital in pinyin}}</div><div class="rom">{{Capital}}</div></div>{{/Capital in simplified Chinese}}
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```


## Card 6 — capital reading

**Front**

```html
{{#Capital in simplified Chinese}}<div class="prompt">Read this capital</div><div class="hanzi hanzi-lg">{{Capital in simplified Chinese}}</div>{{/Capital in simplified Chinese}}
```

**Back**

```html
{{FrontSide}}

<hr id=answer>

<div class="pinyin pinyin-lg">{{Capital in pinyin}}</div><div class="rom">{{Capital}}</div><div class="audio">{{Capital audio}}</div><div class="sep"></div><div class="label cap">capital of</div><div class="english">{{Name}}</div><div class="hanzi sm">{{Name in simplified Chinese}}</div>
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```


## Card 7 — etymology

**Front**

```html
<div class="prompt">Etymology of</div><div class="english">{{Name}}</div><div class="hanzi sm">{{Name in simplified Chinese}}</div><div class="pinyin">{{Name in pinyin}}</div>
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```

**Back**

```html
{{FrontSide}}

<hr id=answer>

<div class="etymology">{{Etymology}}</div>
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>
```
