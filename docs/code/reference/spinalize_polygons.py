from matplotlib import pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch

import numpy
import geopandas as gpd
import shapely
from shapely.wkt import loads
import cartagen4py as c4

polygons = [
    loads('Polygon ((282499.15896787942619994 6246577.45513126626610756, 282490.77501181280240417 6246584.85843994375318289, 282482.2314042717916891 6246593.62964459881186485, 282490.8307609727489762 6246601.28479254059493542, 282508.38265443232376128 6246582.0720604807138443, 282527.38259279477642849 6246574.57894805353134871, 282522.90069882478564978 6246562.99362337775528431, 282507.38949021481676027 6246570.3551049679517746, 282499.15896787942619994 6246577.45513126626610756))'),
    loads('Polygon ((282655.09644928277703002 6246492.13325823657214642, 282645.66182592819677666 6246497.70539804641157389, 282630.29273740161443129 6246506.74087824299931526, 282614.46691543055931106 6246516.07784821186214685, 282600.92191640194505453 6246524.36352359503507614, 282574.44550930592231452 6246539.72169733326882124, 282561.50967246165964752 6246547.55462960060685873, 282554.21213717135833576 6246550.70576493721455336, 282539.01402264443458989 6246556.39611408114433289, 282526.85409722098847851 6246561.19171635527163744, 282522.90069882478564978 6246562.99362337775528431, 282527.38259279477642849 6246574.57894805353134871, 282537.56672388414153829 6246570.53220799658447504, 282541.82962066592881456 6246567.66746176220476627, 282548.50818032352253795 6246566.64199272263795137, 282557.01622470672009513 6246563.95423283521085978, 282595.82197823619935662 6246540.75954940635710955, 282642.08107663987902924 6246513.65402083192020655, 282662.01539257436525077 6246501.90759082045406103, 282655.09644928277703002 6246492.13325823657214642))'),
    loads('Polygon ((282724.9445644092047587 6246450.56480667740106583, 282704.39857288071652874 6246463.22027701325714588, 282675.94321050320286304 6246479.93589389137923717, 282661.0308829503483139 6246488.66990009602159262, 282655.09644928277703002 6246492.13325823657214642, 282662.01539257436525077 6246501.90759082045406103, 282683.16633796418318525 6246489.55988507438451052, 282702.34056207479443401 6246478.11313065979629755, 282713.44319861702388152 6246472.55069546867161989, 282721.71548622305272147 6246484.31005388684570789, 282729.23046403838088736 6246495.91290224902331829, 282740.53477766981814057 6246507.84208715613931417, 282756.07100765727227554 6246522.22946271020919085, 282763.9184963388252072 6246528.81524563021957874, 282773.43231260468019173 6246535.71494169533252716, 282781.55684216966619715 6246520.70530943106859922, 282775.06089339515892789 6246516.40881332661956549, 282769.02253053092863411 6246511.65871283784508705, 282765.39986920647788793 6246508.74781729094684124, 282763.13670071098022163 6246506.75741036795079708, 282757.70669044705573469 6246501.70667825825512409, 282752.58262288302648813 6246496.2014596750959754, 282747.76273128011962399 6246490.54592775274068117, 282743.24701529974117875 6246484.74008328560739756, 282739.03635820018826053 6246478.63184136152267456, 282734.82924173708306625 6246471.91525936406105757, 282731.07882701617199928 6246464.8971685990691185, 282727.93498816550709307 6246457.88262739777565002, 282724.9445644092047587 6246450.56480667740106583))'),
    loads('Polygon ((282879.62448553048307076 6246555.34597144741564989, 282873.19368120637955144 6246539.7951055783778429, 282862.87660719844279811 6246540.64751519076526165, 282862.11750612751347944 6246540.79518154915422201, 282851.04573704744689167 6246541.03480982314795256, 282840.13090262992773205 6246540.36278807651251554, 282833.16057510464452207 6246539.40957946423441172, 282826.79417820833623409 6246538.91616435814648867, 282821.03788638167316094 6246537.81793704908341169, 282814.98271993017988279 6246535.95750293880701065, 282808.32362817507237196 6246533.6372651094570756, 282801.51554384717019275 6246530.85987795237451792, 282794.70834648195886984 6246527.93039985373616219, 282788.0554456384270452 6246524.54554338939487934, 282781.55684216966619715 6246520.70530943106859922, 282773.43231260468019173 6246535.71494169533252716, 282782.50445522315567359 6246540.33067507669329643, 282791.12608908745460212 6246544.18331148568540812, 282803.83329420804511756 6246549.58070843946188688, 282804.13658232754096389 6246549.58247862476855516, 282818.21654101350577548 6246553.61904090642929077, 282834.12682696391129866 6246555.84115317184478045, 282850.04152954171877354 6246557.30280190519988537, 282860.04916507570305839 6246557.51324677187949419, 282879.62448553048307076 6246555.34597144741564989))'),
    loads('Polygon ((283021.72929129039403051 6246422.48502456583082676, 283006.62223733041901141 6246412.51137781981378794, 282996.51805312314536422 6246429.03042147681117058, 282993.76124092983081937 6246433.72918115649372339, 282990.69938289921265095 6246438.73034878727048635, 282987.63752139458665624 6246443.73151816893368959, 282984.11457360477652401 6246449.79463978577405214, 282979.9806537606054917 6246456.61466257553547621, 282975.84672752034384757 6246463.43468866031616926, 282971.86619681783486158 6246469.95142911653965712, 282968.19158489210531116 6246476.01368007343262434, 282964.21368208341300488 6246482.07416901551187038, 282959.6265622602077201 6246488.58738833107054234, 282954.73790920100873336 6246494.79467312432825565, 282949.39519954315619543 6246500.84722575545310974, 282944.05776311468798667 6246505.98726222664117813, 282938.41791383072268218 6246510.97344665694981813, 282932.17236449004849419 6246515.80401246342808008, 282925.77692555275280029 6246520.32952065020799637, 282918.77666653011692688 6246524.54732111934572458, 282911.17158728680806234 6246528.4574119821190834, 282903.87419279507594183 6246531.60883167013525963, 282896.73107964056544006 6246534.30486994236707687, 282889.74313010642072186 6246536.39344007987529039, 282883.21363347989972681 6246537.87630946841090918, 282873.19368120637955144 6246539.7951055783778429, 282879.62448553048307076 6246555.34597144741564989, 282891.16530048317508772 6246552.67556576523929834, 282905.90384541935054585 6246547.74239273741841316, 282918.82440746936481446 6246542.49442702438682318, 282930.53884589835070074 6246536.02268873155117035, 282943.01764657499734312 6246528.49074704758822918, 282952.00686361943371594 6246521.24266938120126724, 282957.20145983475958928 6246514.58087353128939867, 282970.01252240582834929 6246502.03183384146541357, 282984.38570757978595793 6246481.58315044641494751, 283021.72929129039403051 6246422.48502456583082676))'),
]

entries = [
    loads('Point (283014.17576431040652096 6246417.49820119328796864)'),
    loads('Point (282486.0454146628617309 6246597.02487691771239042)'),
]

structural = [
    loads('Point (282718.53675920091336593 6246463.61226381175220013)')
]

fig = plt.figure(1, (12, 8))

#############################################################

sub1 = fig.add_subplot(211)
sub1.set_title('densify=10.0 sigma=5.0 without structural point', pad=10, family='sans-serif')
sub1.axes.get_xaxis().set_visible(False)
sub1.axes.get_yaxis().set_visible(False)

sub2 = fig.add_subplot(212)
sub2.set_title('densify=10.0 sigma=5.0 with structural point', pad=10, family='sans-serif')
sub2.axes.get_xaxis().set_visible(False)
sub2.axes.get_yaxis().set_visible(False)

generalized1 = c4.spinalize_polygons(polygons, 10.0, 5.0, entries)
generalized2 = c4.spinalize_polygons(polygons, 10.0, 5.0, entries, structural)

for s in structural:
    coords = s.coords[0]
    sub2.plot(coords[0], coords[1], linestyle="", marker='o', color="black")

for polygon in polygons:
    poly = Path.make_compound_path(Path(numpy.asarray(polygon.exterior.coords)[:, :2]),*[Path(numpy.asarray(ring.coords)[:, :2]) for ring in polygon.interiors])
    sub1.add_patch(PathPatch(poly, facecolor="lightgray", edgecolor='gray'))
    sub2.add_patch(PathPatch(poly, facecolor="lightgray", edgecolor='gray'))

for g in generalized1:
    path = Path(numpy.asarray(g.coords)[:, :2])
    sub1.add_patch(PathPatch(path, facecolor="none", edgecolor='red', linewidth=1))

for g in generalized2:
    path = Path(numpy.asarray(g.coords)[:, :2])
    sub2.add_patch(PathPatch(path, facecolor="none", edgecolor='red', linewidth=1))

for e in entries:
    coords = e.coords[0]
    sub1.plot(coords[0], coords[1], linestyle="", marker='o', color="red")
    sub2.plot(coords[0], coords[1], linestyle="", marker='o', color="red")

sub1.autoscale_view()
sub2.autoscale_view()
plt.show()