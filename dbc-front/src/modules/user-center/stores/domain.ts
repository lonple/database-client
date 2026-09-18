import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type DomainCode = 'COMPANY' | 'PERSONAL'

const DOMAIN_KEY = 'dbc_domain'

function readStored(): DomainCode {
  const v = localStorage.getItem(DOMAIN_KEY)
  return v === 'PERSONAL' ? 'PERSONAL' : 'COMPANY'
}

/** 公司域 / 个人域上下文（请求头 X-Dbc-Domain） */
export const useDomainStore = defineStore('domain', () => {
  const domain = ref<DomainCode>(readStored())

  const isPersonal = computed(() => domain.value === 'PERSONAL')
  const isCompany = computed(() => domain.value === 'COMPANY')

  function setDomain(next: DomainCode) {
    domain.value = next
    localStorage.setItem(DOMAIN_KEY, next)
  }

  function enterPersonal() {
    setDomain('PERSONAL')
  }

  function exitPersonal() {
    setDomain('COMPANY')
  }

  function clear() {
    domain.value = 'COMPANY'
    localStorage.removeItem(DOMAIN_KEY)
  }

  return { domain, isPersonal, isCompany, setDomain, enterPersonal, exitPersonal, clear }
})
