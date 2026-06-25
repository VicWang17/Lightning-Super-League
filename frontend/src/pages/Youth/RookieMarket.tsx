import { Link } from 'react-router-dom'
import { YouthTabs } from '../../components/youth/YouthTabs'
import { PageHeader } from '../../components/ui/PageHeader'
import { Card, CardContent, CardHeader } from '../../components/ui/Card'

const TIMELINE = [
  {
    day: '第 4 / 8 天',
    title: '青训营刷新',
    desc: '系统根据各队青训投入向青训营补充 17-18 岁新秀，营内最多同时存在 8 人。',
    tone: 'sky',
  },
  {
    day: '赛季中',
    title: '签约或放弃',
    desc: '玩家可随时将青训球员签入一线队（1-2 年新人合同），或主动放弃。被放弃的球员状态标记为“待释放”，暂不可见。',
    tone: 'amber',
  },
  {
    day: '第 25 天',
    title: '赛季末名单结算',
    desc: '所有未签约及被放弃的青训球员统一进入自由市场的“新人保护池”（来源：青训新人），此时对玩家不可直接签约。',
    tone: 'coral',
  },
  {
    day: '第 25 天结算后',
    title: 'AI 优先签约轮',
    desc: '同联赛的 AI 球队按上赛季排名倒序（低排名优先）挑选保护池中的新秀一轮，签走后该球员即从保护池移除。',
    tone: 'lime',
  },
  {
    day: 'AI 优先轮结束后',
    title: '转入普通自由市场',
    desc: '保护池中剩余的新人取消保护标记，成为普通自由市场 listing，所有球队均可查看并签约。',
    tone: 'sky',
  },
]

const toneClasses: Record<string, string> = {
  sky: 'bg-[#59C7EE]/15 border-[#59C7EE]/40 text-[#1F5F43]',
  amber: 'bg-[#FFC247]/15 border-[#FFC247]/40 text-[#8B5A2B]',
  coral: 'bg-[#FF6F59]/12 border-[#FF6F59]/30 text-[#FF6F59]',
  lime: 'bg-[#B9EF3F]/20 border-[#B9EF3F]/60 text-[#1F5F43]',
}

export default function RookieMarket() {
  return (
    <div className="space-y-6 max-w-[1400px]">
      <PageHeader
        title="新人市场"
        subtitle="青训球员赛季末流转链路（当前后端为简化版，无选秀大会）"
      />

      <YouthTabs />

      <Card>
        <CardHeader title="还没到时间！" />
        <CardContent className="p-4">
          <div className="relative pl-6 sm:pl-8">
            <div className="absolute left-[11px] sm:left-[15px] top-2 bottom-2 w-0.5 bg-[#1F5F43]/20" />
            <div className="space-y-5">
              {TIMELINE.map((item, idx) => (
                <div key={idx} className="relative flex items-start gap-4">
                  <div className="absolute -left-6 sm:-left-8 top-1 w-5 h-5 bg-[#B9EF3F] border-2 border-[#1F5F43] rounded-full z-10" />
                  <div className={`flex-1 p-3 border-2 ${toneClasses[item.tone]}`}>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="text-xs font-black px-2 py-0.5 bg-white/70 border border-[#1F5F43]/20">
                        {item.day}
                      </span>
                      <h3 className="text-sm font-black">{item.title}</h3>
                    </div>
                    <p className="text-xs leading-relaxed opacity-90">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader title="当前实现规则" />
          <CardContent className="p-4">
            <ul className="text-sm text-[#466353] space-y-2 list-disc pl-4">
              <li>赛季长度为 25 天，青训刷新日为第 4、8 天。</li>
              <li>没有“选秀大会/志愿排序”流程；赛季末由系统自动把未签约青训球员释放到自由市场。</li>
              <li>释放后先进入“新人保护池”，仅对同联赛 AI 球队开放一轮优先签约。</li>
              <li>AI 优先轮按上赛季联赛排名倒序处理，低排名 AI 队先挑。</li>
              <li>AI 优先轮结束后，剩余新人转为普通自由市场 listing，所有球队均可签约。</li>
              <li>中途主动放弃的球员也会在赛季末一并进入该流程。</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="现在能做什么？" />
          <CardContent className="p-4 space-y-4">
            <p className="text-sm text-[#466353]">
              只有在赛季末 AI 优先轮结束后，青训来源的新人才会出现在自由市场里。你可以前往自由市场，在“来源”筛选中选择“青训新人”查看当前可签约的球员。
            </p>
            <Link
              to="/transfer/free-market"
              className="inline-flex items-center justify-center px-5 py-2.5 bg-[#B9EF3F] text-[#173126] text-sm font-black border-2 border-[#1F5F43] hover:bg-[#FFC247] transition-colors"
            >
              请移步转会市场 →
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
