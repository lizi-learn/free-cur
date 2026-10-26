'use strict';
const $=id=>document.getElementById(id);let catalogue=null;
const node=(tag,text)=>{const value=document.createElement(tag);value.textContent=text;return value;};
function render(){if(!catalogue)return;const query=$('search').value.toLocaleLowerCase(),filter=$('filter').value;
 $('total').textContent=catalogue.themes.length;$('published').textContent=catalogue.themes.filter(x=>x.published).length;$('hidden').textContent=catalogue.themes.filter(x=>!x.published).length;
 $('themes').replaceChildren(...catalogue.themes.filter(x=>(x.name+x.group+x.id).toLocaleLowerCase().includes(query)&&(filter==='all'||x.published===(filter==='published'))).map(theme=>{
  const row=document.createElement('tr'),name=node('td',theme.name);name.append(node('small',' '+theme.id));row.append(name,node('td',theme.group),node('td',theme.pixel?'像素动态':'旧版头像'));
  const state=node('td',theme.published?'已上架':'已下架');state.className=theme.published?'published':'hidden';row.append(state);
  const cell=document.createElement('td'),button=node('button',theme.published?'下架':'上架');button.onclick=async()=>{button.disabled=true;try{
   const response=await fetch('/api/admin/catalog',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':catalogue.csrf},body:JSON.stringify({id:theme.id,published:!theme.published,revision:catalogue.revision})});
   const result=await response.json();if(!response.ok)throw Error(result.error||'更新失败');await load();$('status').textContent=theme.name+'已'+(theme.published?'下架':'上架')+'；客户端下次同步生效。';
  }catch(error){$('status').textContent=error.message;button.disabled=false;}};cell.append(button);row.append(cell);return row;}));
 $('audit').replaceChildren(...catalogue.history.map(x=>node('div',new Date(x.at*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})+' · '+x.id+' · '+(x.published?'上架':'下架'))));
}
async function load(){try{const response=await fetch('/api/admin/catalog',{cache:'no-store'});if(!response.ok)throw Error('读取失败，请重新验证身份');catalogue=await response.json();render();$('status').textContent='目录已更新。';}catch(error){$('status').textContent=error.message;}}
$('search').oninput=render;$('filter').onchange=render;$('refresh').onclick=load;load();
