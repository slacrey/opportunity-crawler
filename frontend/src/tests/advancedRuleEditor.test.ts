import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AdvancedRuleEditor from '../components/AdvancedRuleEditor.vue'

describe('AdvancedRuleEditor', () => {
  it('emits parsed advanced rule payload for preview', async () => {
    const wrapper = mount(AdvancedRuleEditor, {
      props: {
        modelValue: {
          adapter_mode: 'manual_import',
          entry_url: 'manual://wechat',
          login_mode: 'not_required'
        }
      }
    })

    await wrapper.find('[data-test="preview"]').trigger('click')

    expect(wrapper.emitted('preview')?.[0][0]).toMatchObject({
      adapter_mode: 'manual_import',
      entry_url: 'manual://wechat'
    })
  })
})

