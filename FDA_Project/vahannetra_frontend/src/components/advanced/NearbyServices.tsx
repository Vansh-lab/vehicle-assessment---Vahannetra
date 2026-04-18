import { Card } from "@/components/ui/card";

interface NearbyService {
  id: string;
  name: string;
  distanceKm: number;
  dent: string;
  scratch: string;
  paint: string;
  rating: number;
}

interface NearbyServicesProps {
  items: NearbyService[];
}

export function NearbyServices({ items }: NearbyServicesProps) {
  return (
    <Card className="space-y-3 overflow-auto">
      <p className="text-sm font-semibold text-slate-100">Nearby Services Pricing Matrix</p>
      <table className="w-full min-w-[640px] text-xs text-slate-300">
        <thead>
          <tr className="text-left text-slate-400">
            <th className="py-2 pr-3">Garage</th>
            <th className="py-2 pr-3">Distance</th>
            <th className="py-2 pr-3">Dent</th>
            <th className="py-2 pr-3">Scratch</th>
            <th className="py-2 pr-3">Paint</th>
            <th className="py-2 pr-3">Rating</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-t border-white/10">
              <td className="py-2 pr-3 font-medium text-slate-200">{item.name}</td>
              <td className="py-2 pr-3">{item.distanceKm.toFixed(1)} km</td>
              <td className="py-2 pr-3">{item.dent}</td>
              <td className="py-2 pr-3">{item.scratch}</td>
              <td className="py-2 pr-3">{item.paint}</td>
              <td className="py-2 pr-3">{item.rating.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
