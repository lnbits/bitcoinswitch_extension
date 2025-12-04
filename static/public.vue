<template id="page-bitcoinswitch-public">
  <div class="row q-col-gutter-md justify-center">
    <div class="col-12 col-sm-6 col-md-5 col-lg-4">
      <q-card class="q-pa-lg">
        <q-card-section class="q-pa-none text-center">
          <lnbits-qrcode-lnurl
            :url="activeUrl"
            @update:lnurl="v => (lnurl = v)"
          ></lnbits-qrcode-lnurl>
        </q-card-section>
      </q-card>
    </div>
    <div class="col-12 col-sm-6 col-md-5 col-lg-4 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <h6 class="text-subtitle1 q-mb-sm q-mt-none">Bitcoinswitch</h6>
          <p class="text-caption q-mb-md">
            Turn on and off things with bitcoin!
          </p>
          <a
            class="text-secondary"
            href="https://github.com/lnbits/bitcoinSwitch"
          >
            https://github.com/lnbits/bitcoinSwitch</a
          >
        </q-card-section>
      </q-card>
      <q-card v-if="bitcoinswitch">
        <q-card-section>
          <h6
            class="text-subtitle1 q-mb-sm q-mt-none"
            v-text="bitcoinswitch.title"
          ></h6>
          <q-select
            v-model="activeSwitch"
            :options="bitcoinswitch.switches"
            option-value="pin"
            :option-label="option => 'Pin ' + option.pin + ' - ' + option.label"
            label="Select a pin"
            outlined
            dense
            class="q-mb-md"
          ></q-select>
          <q-btn
            color="primary"
            class="full-width"
            :label="$t('copy') + ' LNURL'"
            @click="copyText(lnurl)"
          ></q-btn>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>
