// Native Vulkan shaders. Texture coordinates arrive in decoded texel units.
struct Push { float4 row0; float4 row1; float4 row2; float4 row3; float4 uv; uint4 control; float4 fog; uint4 flags; };
[[vk::push_constant]] Push pc;
[[vk::binding(0,0)]] Texture2D<float4> tex;
[[vk::binding(1,0)]] SamplerState samp;
struct In {
 [[vk::location(0)]] float4 pos:POSITION;
 [[vk::location(1)]] float4 color:COLOR;
 [[vk::location(2)]] float2 uv:TEXCOORD0;
 [[vk::location(3)]] float fog:FOG;
 [[vk::location(4)]] float q:TEXCOORD1;
};
struct Out { float4 pos:SV_Position; float4 color:COLOR; float2 uv:TEXCOORD0; float fog:FOG; float q:TEXCOORD1; };
Out VSMain(In i) {
 if(pc.flags.w!=0) { i.pos.xyz*=i.pos.w; }
 Out o; o.pos=float4(dot(pc.row0,i.pos),dot(pc.row1,i.pos),dot(pc.row2,i.pos),dot(pc.row3,i.pos));
 o.uv=i.uv*pc.uv.xy+pc.uv.zw; o.color=i.color; o.fog=i.fog; o.q=i.q; return o;
}
bool compareAlpha(uint f,uint a,uint b) {
 switch(f) { case 0:return false;case 1:return true;case 2:return a==b;case 3:return a!=b;case 4:return a<b;case 5:return a<=b;case 6:return a>b;default:return a>=b; }
}
float4 PSMain(Out i):SV_Target {
 float4 c=saturate(i.color);
 if(pc.flags.x!=0) {
  float2 uv=i.uv/(abs(i.q)>1e-12?i.q:1.0);
  float4 t=tex.Sample(samp,uv); bool a=(pc.control.y&256)!=0;
  switch(pc.control.y&255) {
   case 0:c=float4(c.rgb*t.rgb,a?c.a*t.a:c.a);break;
   case 1:c.rgb=a?lerp(c.rgb,t.rgb,t.a):t.rgb;break;
   case 2:c=float4(lerp(c.rgb,pc.fog.rgb,t.rgb),a?c.a*t.a:c.a);break;
   case 3:c=float4(t.rgb,a?t.a:c.a);break;
   case 4:c=float4(c.rgb+t.rgb,a?c.a*t.a:c.a);break;
  }
  if((pc.control.y&65536)!=0)c.rgb*=2;
 }
 if(pc.flags.y!=0) {
  float3 f=float3(pc.control.z&255,(pc.control.z>>8)&255,(pc.control.z>>16)&255)/255.0;
  float k=saturate(i.fog); if(pc.flags.z!=0)k=k*k*(3-2*k); c.rgb=lerp(f,c.rgb,k);
 }
 uint ac=pc.control.x;
 if((ac&255)!=0 && !compareAlpha((ac>>8)&255, uint(floor(saturate(c.a)*255+0.5))&(ac>>24), ((ac>>16)&255)&(ac>>24))) discard;
 c=saturate(c);
 if(pc.control.w==0)c=float4(floor(c.rgb*float3(31,63,31)+0.5)/float3(31,63,31),1);
 else if(pc.control.w==1)c=float4(floor(c.rgb*31+0.5)/31,c.a>=0.5?1:0);
 else if(pc.control.w==2)c=floor(c*15+0.5)/15;
 return c;
}
