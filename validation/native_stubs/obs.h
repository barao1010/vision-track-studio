#pragma once
struct obs_scene;
struct obs_source { unsigned width=1000,height=600; obs_scene *scene=nullptr; };
struct vec2 { float x=1,y=1; };
struct obs_transform_info { vec2 scale; };
struct obs_sceneitem_crop { int left=0,top=0,right=0,bottom=0; };
struct obs_sceneitem { obs_source source; obs_transform_info info; obs_sceneitem_crop crop; int refs=0; };
struct obs_scene { obs_sceneitem *item=nullptr; };
using obs_source_t=obs_source;
using obs_scene_t=obs_scene;
using obs_sceneitem_t=obs_sceneitem;
inline auto obs_sceneitem_get_source(obs_sceneitem_t *i){return &i->source;}
inline auto obs_source_get_width(obs_source_t *s){return s->width;}
inline auto obs_source_get_height(obs_source_t *s){return s->height;}
inline void obs_sceneitem_get_crop(obs_sceneitem_t *i,obs_sceneitem_crop *v){*v=i->crop;}
inline void obs_sceneitem_get_info2(obs_sceneitem_t *i,obs_transform_info *v){*v=i->info;}
inline void obs_sceneitem_set_crop(obs_sceneitem_t *i,const obs_sceneitem_crop *v){i->crop=*v;}
inline void obs_sceneitem_set_info2(obs_sceneitem_t *i,const obs_transform_info *v){i->info=*v;}
inline void obs_sceneitem_addref(obs_sceneitem_t *i){++i->refs;}
inline void obs_sceneitem_release(obs_sceneitem_t *i){--i->refs;}
inline auto obs_scene_find_source_recursive(obs_scene_t *s,const char *){return s->item;}
inline auto obs_scene_from_source(obs_source_t *s){return s->scene;}
using OBSScene=obs_scene_t *;
using OBSSource=obs_source_t *;
struct OBSBasic {
 obs_scene_t *preview=nullptr;obs_source_t *program=nullptr;bool studio=true;
 auto GetCurrentScene(){return preview;}
 auto GetProgramSource(){return program;}
 bool IsPreviewProgramMode(){return studio;}
};
