import { useState } from "react"

import { SketchyDefs } from "@/components/SketchyDefs"
import { Header } from "@/components/layout/Header"
import { ActivityTab } from "@/components/tabs/ActivityTab"
import { OverviewTab } from "@/components/tabs/OverviewTab"
import { PositionsTab } from "@/components/tabs/PositionsTab"
import { SettingsTab } from "@/components/tabs/SettingsTab"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

const TABS = [
  { value: "overview", label: "Overview" },
  { value: "positions", label: "Positions" },
  { value: "activity", label: "Activity Log" },
  { value: "settings", label: "Settings" },
]

function App() {
  const [activeTab, setActiveTab] = useState("overview")

  return (
    <>
      <SketchyDefs />
      <div className="mx-auto max-w-[1440px] px-8 pt-7 pb-12">
        <Header activeTab={activeTab} />
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            {TABS.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
          {/* Overview children carry their own staggered fadeUp (0.6s); the
              other tabs fade up as a whole (0.4s), per the reference. */}
          <TabsContent value="overview">
            <OverviewTab />
          </TabsContent>
          <TabsContent value="positions" className="fade-up-tab">
            <PositionsTab />
          </TabsContent>
          <TabsContent value="activity" className="fade-up-tab">
            <ActivityTab />
          </TabsContent>
          <TabsContent value="settings" className="fade-up-tab">
            <SettingsTab />
          </TabsContent>
        </Tabs>
      </div>
    </>
  )
}

export default App
