window.PageBitcoinswitchPublic = {
  template: "#page-bitcoinswitch-public",
  mixins: [window.windowMixin],
  data() {
    return {
      bs: null,
      url: '',
      lnurl: '',
      activeUrl: '',
      activeSwitch: null
    }
  },
  watch: {
    activeSwitch(val) {
      this.activeUrl = `${this.url}?pin=${val.pin}`
    }
  },
  async created() {
    this.g.public = true
    const bsId = this.$route.params.id
    this.url = `${window.location.origin}/bitcoinswitch/api/v1/lnurl/${bsId}`
    try {
        const res = await LNbits.api.request("GET", `/bitcoinswitch/api/v1/${bsId}`)
        this.bs = res.data
    } catch (error) {
        LNbits.utils.notifyApiError(error)
        return
    }
    this.activeSwitch = this.bs.switches[0]
    this.activeUrl = `${this.url}?pin=${this.activeSwitch.pin}`
  }
}
