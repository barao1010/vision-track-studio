// SPDX-License-Identifier: GPL-2.0-or-later
// Compiles the production zoom header against stateful API substitutes.
// This isolates ownership/restoration; it does not simulate OBS rendering.
#include <obs.h>
#include "../tracking/FixedCameraSceneZoom.hpp"
#include <cassert>
#include <cmath>

int main() {
 obs_sceneitem_t a,b;
 a.crop.left=25;b.crop.right=50;
 a.info.scale.x=1.5f;b.info.scale.y=.75f;
 obs_scene_t sceneA{&a},sceneB{&b};
 obs_source_t live;live.scene=&sceneB;
 OBSBasic main;main.preview=&sceneA;main.program=&live;
 FixedCameraSceneZoom zoom(&main);zoom.setSource("camera");
 assert(zoom.apply(.1,.1,.5,.5));
 assert(a.crop.left==100 && b.crop.right==400);
 // Swap roles repeatedly, the real studio-transition regression trigger.
 for (int i=0;i<10;++i) {
  main.preview=i%2 ? &sceneA : &sceneB;
  live.scene=i%2 ? &sceneB : &sceneA;
  assert(zoom.apply(.2,.1,.5,.5));
  assert(a.crop.left==200 && b.crop.left==200);
  assert(a.refs==1 && b.refs==1);
 }
 zoom.restore();
 assert(a.crop.left==25 && a.crop.right==0);
 assert(b.crop.left==0 && b.crop.right==50);
 assert(a.info.scale.x==1.5f && b.info.scale.y==.75f);
 assert(a.refs==0 && b.refs==0);
 // The same item in preview/program must not be snapshotted twice.
 main.preview=&sceneA;live.scene=&sceneA;
 assert(zoom.apply(.1,.1,.5,.5));assert(a.refs==1);
 zoom.restore();assert(a.refs==0 && a.crop.left==25);
 // Existing over-crop cannot underflow an unsigned scale computation.
 a.crop.left=1200;
 assert(!zoom.apply(.1,.1,.5,.5));
 assert(a.info.scale.x==1.5f);
 zoom.restore();assert(a.crop.left==1200 && a.refs==0);
}
