#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <aom/aomcx.h>
#include <aom/aomdx.h>
#include <aom/aom_encoder.h>
#include <aom/aom_decoder.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"Failed at line %d: %s\n",__LINE__,#x); return 1; } } while(0)
static int roundtrip(int highbitdepth) {
    aom_codec_enc_cfg_t config;
    aom_codec_ctx_t enc = {0}, dec = {0};
    CHECK(aom_codec_enc_config_default(aom_codec_av1_cx(), &config, AOM_USAGE_REALTIME) == AOM_CODEC_OK);
    config.g_w = 64; config.g_h = 64;
    config.g_timebase.num = 1; config.g_timebase.den = 30;
    config.g_lag_in_frames = 0; config.g_threads = 2;
    config.rc_target_bitrate = 100;
    config.g_bit_depth = highbitdepth ? AOM_BITS_10 : AOM_BITS_8;
    config.g_input_bit_depth = highbitdepth ? 10 : 8;
    CHECK(aom_codec_enc_init(&enc, aom_codec_av1_cx(), &config, highbitdepth ? AOM_CODEC_USE_HIGHBITDEPTH : 0) == AOM_CODEC_OK);
    CHECK(aom_codec_control(&enc, AOME_SET_CPUUSED, 8) == AOM_CODEC_OK);
    CHECK(aom_codec_dec_init(&dec, aom_codec_av1_dx(), NULL, 0) == AOM_CODEC_OK);
    aom_image_t image;
    CHECK(aom_img_alloc(&image, highbitdepth ? AOM_IMG_FMT_I42016 : AOM_IMG_FMT_I420,64,64,1));
    image.bit_depth = highbitdepth ? 10 : 8;
    for (int plane=0; plane<3; plane++) {
        int size = plane ? 32 : 64;
        for (int row=0; row<size; row++) {
            unsigned char *pixels = image.planes[plane]+row*image.stride[plane];
            if (highbitdepth) {
                for (int col=0; col<size; col++) ((uint16_t *)pixels)[col] = (plane ? 128 : 80) << 2;
            } else {
                memset(pixels,plane ? 128 : 80,size);
            }
        }
    }
    CHECK(aom_codec_encode(&enc,&image,0,1,AOM_EFLAG_FORCE_KF) == AOM_CODEC_OK);
    aom_codec_iter_t packets = NULL;
    const aom_codec_cx_pkt_t *packet;
    int frames = 0;
    while ((packet = aom_codec_get_cx_data(&enc,&packets))) {
        if (packet->kind != AOM_CODEC_CX_FRAME_PKT) continue;
        CHECK(aom_codec_decode(&dec,packet->data.frame.buf,packet->data.frame.sz,NULL) == AOM_CODEC_OK);
        aom_codec_iter_t images = NULL;
        aom_image_t *decoded;
        while ((decoded = aom_codec_get_frame(&dec,&images))) {
            CHECK(decoded->d_w == 64 && decoded->d_h == 64);
            CHECK(decoded->bit_depth == (unsigned int)(highbitdepth ? 10 : 8));
            int pixel = (decoded->fmt & AOM_IMG_FMT_HIGHBITDEPTH) ? ((uint16_t *)decoded->planes[0])[0] : decoded->planes[0][0];
            int scale = highbitdepth ? 4 : 1;
            CHECK(pixel >= 70*scale && pixel <= 90*scale);
            frames++;
        }
    }
    CHECK(frames == 1);
    aom_img_free(&image);
    CHECK(aom_codec_destroy(&enc) == AOM_CODEC_OK);
    CHECK(aom_codec_destroy(&dec) == AOM_CODEC_OK);
    return 0;
}
int main(void) {
    CHECK(roundtrip(0) == 0);
    CHECK(roundtrip(1) == 0);
    puts(aom_codec_version_str());
    puts("AV1 8-bit and 10-bit realtime encode/decode round trips passed");
    return 0;
}
