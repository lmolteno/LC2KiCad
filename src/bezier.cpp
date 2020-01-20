/*
    Copyright (c) 2020 Harrison Wade, aka "RigoLigo RLC"

    This file is part of LC2KiCad.

    LC2KiCad is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    LC2KiCad is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with LC2KiCad. If not, see <https://www.gnu.org/licenses/>.
*/

#include "elements.hpp"
#include "include.hpp"
#include "consts.hpp"

using std::vector;

namespace lc2kicad
{
  coordinates middlepoint(coordinates coord1, coordinates coord2, float t)
  {
    return (coord1 - coord2) * t + coord1;
  }

  vector<coordinates>* render_bezier_curve(vector<coordinates>& control_points, int iterations)
  {
    if(iterations < 2)
      throw "Invalid iterations for Bezier curve renderer.";

    vector<coordinates> cp, *ret = new vector<coordinates>;
    for(int i = 0; i < control_points.size(); i++)
      cp[i] = control_points[i];
    
    float t = 0;
    (*ret)[0] = cp[0];
    for(int i = 1; i < iterations; i++)
    {
      t = float (i) / 1.0f;
      (*ret)[1] = middlepoint(cp[i], cp[i + 1], t);
    }
    (*ret).push_back(cp[cp.size() - 1]);
    return ret;
  }
}