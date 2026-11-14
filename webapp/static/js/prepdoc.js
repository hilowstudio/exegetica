/* A Prep Room document as markdown: the compact renderer and the student copy. Shared by the Prep Room
   (static/js/generate.js) and a class's copy on its shelf (templates/doc.html, decision 0029), so the Student view
   and what the class sees are drawn by the same code. Classic script: its functions are globals. */
"use strict";
// ---- the compact markdown renderer ----
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function inl(s){return esc(s).replace(/`([^`]+)`/g,(m,c)=>"<code>"+c+"</code>").replace(/_{3,}/g,m=>"<span class='blank' style='min-width:"+Math.min(26,Math.max(3,m.length*0.55)).toFixed(1)+"em'></span>").replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>").replace(/(^|[^*])\*([^*\n]+)\*/g,"$1<em>$2</em>").replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');}
function md(src){const L=src.replace(/\r\n/g,"\n").split("\n");let h="",i=0;const sep=s=>/^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(s);const cells=s=>s.replace(/^\s*\|/,"").replace(/\|\s*$/,"").split("|").map(c=>c.trim());
  while(i<L.length){let l=L[i];
    if(/^```/.test(l)){i++;let b=[];while(i<L.length&&!/^```/.test(L[i])){b.push(L[i]);i++;}i++;h+="<pre><code>"+esc(b.join("\n"))+"</code></pre>";continue;}
    if(/^\s*$/.test(l)){i++;continue;}
    if(/^#{1,4}\s/.test(l)){const n=l.match(/^#+/)[0].length;h+="<h"+n+">"+inl(l.replace(/^#+\s/,""))+"</h"+n+">";i++;continue;}
    if(/^\s*_{3,}\s*$/.test(l)){let n=0;while(i<L.length&&/^\s*_{3,}\s*$/.test(L[i])){n++;i++;}for(let k=0;k<n;k++)h+="<div class='writeline'></div>";continue;}
    if(/^\s*(-{3,}|\*{3,})\s*$/.test(l)){h+="<hr>";i++;continue;}
    if(/^\s*>/.test(l)){let b=[];while(i<L.length&&/^\s*>/.test(L[i])){b.push(L[i].replace(/^\s*>\s?/,""));i++;}h+="<blockquote>"+md(b.join("\n"))+"</blockquote>";continue;}
    if(l.includes("|")&&i+1<L.length&&sep(L[i+1])){const hd=cells(l);i+=2;const rs=[];while(i<L.length&&L[i].includes("|")&&!/^\s*$/.test(L[i])){rs.push(cells(L[i]));i++;}h+=Shell.table(hd,rs,inl);continue;}
    if(/^\s*[-*]\s+/.test(l)){let b=[];while(i<L.length&&/^\s*[-*]\s+/.test(L[i])){b.push("<li>"+inl(L[i].replace(/^\s*[-*]\s+/,""))+"</li>");i++;}h+="<ul>"+b.join("")+"</ul>";continue;}
    if(/^\s*\d+[.)]\s+/.test(l)){let b=[];while(i<L.length&&/^\s*\d+[.)]\s+/.test(L[i])){const mm=L[i].match(/^\s*(\d+)[.)]\s+/);b.push("<li value='"+mm[1]+"'>"+inl(L[i].replace(/^\s*\d+[.)]\s+/,""))+"</li>");i++;}h+="<ol>"+b.join("")+"</ol>";continue;}
    let b=[];while(i<L.length&&!/^\s*$/.test(L[i])&&!/^```/.test(L[i])&&!/^#{1,4}\s/.test(L[i])&&!/^\s*[-*]\s+/.test(L[i])&&!/^\s*>/.test(L[i])&&!/^\s*_{3,}\s*$/.test(L[i])&&!/^\s*(-{3,}|\*{3,})\s*$/.test(L[i])){b.push(L[i]);i++;}h+="<p>"+inl(b.join("\n")).replace(/\n/g,"<br>")+"</p>";}
  return h;}

// ---- the student copy: the teacher-only sections out (mirrors prep_catalog.student_copy) ----
const TEACHER_HEAD=/^(#{1,6})\s+(?:answer key|answers|teaching notes|teacher notes|notes for the teacher|for the teacher|teacher'?s? (?:guide|notes|key)|.*\((?:teacher|teacher only|for the teacher)\))\s*:?\s*$/i;
const TEACHER_LINE=/^\s*(?:\*\*)?(?:standards|objectives? \(teacher\))(?:\*\*)?\s*:/i;
const BAND_LINE=/^\s*(?:>\s*)?(?:\*\*)?grade[ -]band(?:\*\*)?\s*:/i;
function studentCopy(src){const out=[];let skip=0;
  for(const line of src.split("\n")){const head=line.match(/^(#{1,6})\s/);
    if(skip){if(head&&head[1].length<=skip)skip=0;else continue;}
    const m=line.trim().match(TEACHER_HEAD);
    if(m){skip=m[1].length;while(out.length&&/^\s*(---|\*\*\*|___)?\s*$/.test(out[out.length-1]))out.pop();continue;}
    if(TEACHER_LINE.test(line)||BAND_LINE.test(line))continue;out.push(line);}
  while(out.length&&/^\s*(---|\*\*\*|___)?\s*$/.test(out[out.length-1]))out.pop();
  return out.join("\n")+"\n";}
function hasTeacherPart(src){return src.split("\n").some(l=>TEACHER_HEAD.test(l.trim()));}

