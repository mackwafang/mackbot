import numpy as np

# shell calc from https://github.com/WoWs-Builder-Team/WoWs-ShipBuilder/blob/development/WoWsShipBuilder.Common/Features/BallisticCharts/BallisticHelper.cs

gun_data = {"_id":{"$oid":"647f80468dc575724f45d61e"},"profile":{"artillery":{"shotDelay":30,"caliber":0.46,"numBarrels":3,"burn_probability":35,"sigma":2.1,"range":26630,"dispersion_h":{"5000":120,"10000":156,"15000":192,"20000":228,"25000":264,"26630":276},"dispersion_v":{"5000":42,"10000":78,"15000":48,"20000":91,"25000":145,"26630":165},"transverse_speed":3,"pen":{"he":77,"ap":0,"cs":0},"max_damage":{"he":7300,"ap":14800,"cs":0},"gun_dpm":{"he":131400,"ap":266400,"cs":0},"speed":{"he":805,"ap":780,"cs":0},"krupp":{"he":240,"ap":2574,"cs":0},"mass":{"he":1360,"ap":1460,"cs":0},"drag":{"he":0.543,"ap":0.292,"cs":0},"ammo_name":{"he":"460 mm HE Type0","ap":"460 mm AP/APC Type91","cs":""},"normalization":{"he":8,"ap":6,"cs":0},"fuse_time":{"he":0.001,"ap":0.033,"cs":0},"fuse_time_threshold":{"he":2,"ap":77,"cs":0},"ricochet":{"he":91,"ap":45,"cs":0},"ricochet_always":{"he":60,"ap":60,"cs":0},"turrets":{"460 mm/45 Type 94 in a triple turret":{"numBarrels":3,"count":3,"armor":{"65568":250,"65569":270,"65571":190,"65635":135,"65636":650}}},"taperDist":5000,"idealRadius":10,"idealDistance":1000,"minRadius":2.8,"radiusOnMax":0.8,"radiusOnZero":0.2,"radiusOnDelim":0.6,"delim":0.5}},"name":"460 mm/45 Type 94 in a triple turret","image":"https://glossary-wows-global.gcdn.co/icons/module/icon_module_Artillery_dea4595bc2cd93d9ce334c9b5a8d3d0738bd57088de2a5ac144aba65e5113e02.png","tag":"PJUA911_B10_ART_STOCK","module_id_str":"PJUA911","module_id":{"$numberLong":"3339693776"},"type":"Artillery","price_credit":2300000,"hash":"0da17b54e999edfae013910c889bc5295c3e48c64812780d3c8aa75f6a0dcb4c"}

# physical constants
G = 9.8                     # gravitational constant        (m/s^2)
T0 = 288.15                 # temperature at sea level      (K)
L = 0.0065                  # atmospheric lapse rate        (C/m)
P0 = 101325                 # preasure at sea level         (Pa)
R = 8.31447                 # ideal gas constant            (J / (mol K))
M = 0.0289644               # molarity of air at sea level  (kg / mol)

# cacluation params
MAX_ANGLES = 600            # max angle                     (degrees)
ANGLE_STEP = 0.00174533     # angle step                    (degrees 60 * Math.PI / 180. / n_angle //ELEV. ANGLES 0-30 deg, at launch)
DT = 0.02                   # time step                     (seconds)

TIMESCALE = 2.61

calculationAngles = [i * ANGLE_STEP for i in range(MAX_ANGLES)]

class Shell:
    def __init__(self, data: dict):
        assert data['type'] == 'Artillery'
        param = data['profile']['artillery']

        self.caliber = param['caliber']
        self.v0 = param['speed']
        self.mass = param['mass']
        self.krupp = param['krupp']
        self.drag = param['drag']
        self.pen = param['pen']
        self.overmatch_limit = self.caliber * 1000 / 14.3
        self.name = data['name']

class Ballistic:
    def __init__(self, penetration: float, velocity: float, flight_time: float, impact_angle: float, coordinates: np.array):
        """
        data container to store trajectory data
        Args:
            penetration (float): petration (cm)
            velocity (float): shell velocity (m/s)
            flight_time (float): time (s)
            impact_angle (float): angle (degree)
            coordinates (np.array): a list of np.array 3d vector
        """
        assert coordinates.shape[1] == 2
        self.penetration = penetration
        self.velocity = velocity
        self.flight_time = flight_time
        self.impact_angle = impact_angle
        self.coordinates = coordinates.copy()

    def __str__(self):
        return f"pen: {self.penetration:0.2f}mm, velocity: {self.velocity}m/s, time: {self.flight_time:0.2f}s, impact angle: {self.impact_angle:0.2f}deg, dist: {self.coordinates[-1][0]:0.1f}"

class TrajectoryData:
    def __init__(self, trajectory: dict):
        """
        data container for calc_ballistic
        Args:
            trajectory (dict): dict form calc_ballistic
        """

        self.data = trajectory.copy()

    def find_gun_angle_at_max_range(self):
        return list(self.data.keys())[-1]

    def get_trajectory_at_range(self, dist: float):
        """
        return trajectory data at specified range
        Args:
            dist (float): desired distance in meters

        Returns:
            (gun_angle, Ballistic)
        """
        for gun_angle, traj in self.data.items():
            if traj.coordinates[-1][0] >= dist:
                return gun_angle, traj
        else:
            return gun_angle, traj

    def get_trajectory_at_max_range(self):
        """
        return trajectory data at max range
        Args:

        Returns:
            (gun_angle, Ballistic)
        """
        angle = self.find_gun_angle_at_max_range()
        return angle, self.data[angle]

def calc_pen(velocity: float, diameter: float, mass: float, krupp: float):
    """
    find penetration at certain shell velocity
    Args:
        velocity (float): shell velocity (m/s)
        diameter (float): shell diameter (cm)
        mass (float): shell mass (kg)
        krupp (float): shell krupp
        ammo_type (str): shell_type
    Returns:
        penetration value in mm
    """
    return 0.00046905491615181766 * np.power(velocity, 1.4822064892953855) * np.power(diameter, -0.6521) * np.power(mass, 0.5506) * (krupp / 2400)

def get_normalization_angles(caliber: float):
    """
    get penetration normalization
    Args:
        caliber (float): shell diameter (cm)

    Returns:
        normalized angle
    """
    if caliber <= 0.139:
        return 10 * np.pi / 180
    if caliber <= 0.152:
        return 8.5 * np.pi / 180
    if caliber <= 0.24:
        return 7 * np.pi / 180
    if caliber < 0.51:
        return 6 * np.pi / 180
    return 15 * np.pi / 180

def calc_ballistic(shell: Shell, max_range: float, ammo_type: str):
    """
    calculate ballistic trajectory of all possible gun angle (0 - 60deg)
    Args:
        shell (Shell): shell data genereated from Shell()
        max_range (float): maximum distance in meters
        ammo_type (str): ammo_type

    Returns:
        TrajectoryData - trajectory data
    """
    assert ammo_type in ['he', 'cs', 'ap']

    gun_angle_dict = {}

    k = 0.5 * shell.drag[ammo_type] * np.power(shell.caliber / 2, 2) * np.pi / shell.mass[ammo_type]

    # penetration at 0 degree
    init_pen = shell.pen[ammo_type] if ammo_type != 'ap' else calc_pen(shell.v0['ap'], shell.caliber, shell.mass['ap'], shell.krupp['ap'])
    init_ballistic = Ballistic(init_pen, shell.v0[ammo_type], 0, 0, np.array([[0,0]]))
    gun_angle_dict[0] = init_ballistic

    last_range = 0

    for angle in calculationAngles:
        # for each angles in set of gun angles to calculate
        coord = np.array([[0,0]])

        # variable init
        x, y, t = 0, 0, 0
        v_x = shell.v0[ammo_type] * np.cos(angle)
        v_y = shell.v0[ammo_type] * np.sin(angle)

        # calcuate trajectory that this gun angle
        while y >= 0:
            x += DT * v_x
            y += DT * v_y

            T = T0 - (L * y)
            p = P0 * np.power(T / T0, G * M / R / L)
            rhoG = (p * M) / R / T
            speed = np.sqrt((v_x * v_x) + (v_y * v_y))
            v_x -= DT * k * rhoG * v_x * speed
            v_y = v_y - (DT * G) - (DT * k * rhoG * v_y * speed)
            t += DT

            if y >= 0:
                coord = np.concatenate((coord, np.array([[x, y]])))

        v_impact = np.sqrt((v_x * v_x) + (v_y * v_y))
        impact_angle = np.arctan2(np.abs(v_y), np.abs(v_x)) * (180 / np.pi)
        pen = shell.pen[ammo_type] if ammo_type != 'ap' else calc_pen(v_impact, shell.caliber, shell.mass['ap'], shell.krupp['ap'])

        if x > max_range or x < last_range:
            break

        ballistic = Ballistic(pen, v_impact, t / TIMESCALE, impact_angle, coord)
        gun_angle_dict[angle] = ballistic
    return TrajectoryData(gun_angle_dict)

def calc_dispersion(gun_module: dict, gun_range: float):
    """
    calculate dispersion at any range
    Args:
        gun_module (dict): artillery module data
        gun_range (float): gun range in m

    Returns:
        tuple: (horizontal dispersion, vertical dispersion) in meters
    """
    gun_data = gun_module['profile']['artillery']
    r = gun_range / 30

    max_gun_range = gun_data['range'] / 30
    taper_dist = gun_data['taperDist'] / 30
    delim_dist = gun_data['delim'] * max_gun_range
    h_disp_at_ideal = gun_data['idealRadius']# * 30  # Horizontal dispersion at idealDistance, in units of 30m
    range_for_ideal = gun_data['idealDistance']# * 30  # Distance at which idealRadius applies, in units of 30m.
    min_radius = gun_data['minRadius']# * 30
    if r <= taper_dist:
        h_disp = r * (h_disp_at_ideal - min_radius) / range_for_ideal + min_radius * (r / taper_dist)  # lerp(gun_data['minRadius'] * 30, h_disp_at_ideal, r / range_for_ideal))
    else:
        h_disp = r * (h_disp_at_ideal - min_radius) / range_for_ideal + min_radius

    if r <= delim_dist:
        v_coef = gun_data['radiusOnZero'] + (gun_data['radiusOnDelim'] - gun_data['radiusOnZero']) * (r / delim_dist)
    else:
        v_coef = gun_data['radiusOnZero'] + (gun_data['radiusOnDelim'] - gun_data['radiusOnZero']) * (r - delim_dist) / (max_gun_range - delim_dist)
    v_disp = h_disp * v_coef

    return round(h_disp * 30) * 2, round(v_disp * 30) * 2

def total_distance_traveled(traj: np.array):
    """
    Find total distance traveled by a salvo
    Args:
        traj (np.array): data generated by TrajectoryData.coordinates

    Returns:
        float
    """
    d = 0
    prev_x, prev_y = 0, 0
    for index, (x, y) in enumerate(traj):
        if index == 0:
            pass
        d += np.sqrt(((x - prev_x) ** 2) + ((y - prev_y) ** 2))
        prev_x = x
        prev_y = y
    return d / 1000

def within_dispersion(point: tuple, dispersion: tuple):
    """
    return if point within eclipse
    Args:
        point (tuple): point (x, y)
        dispersion (tuple): eclipse with dimension (w, h)

    Returns:
        Boolean
    """
    assert len(point) == 2
    assert len(dispersion) == 2

    x, y = point
    disp_w, disp_h = dispersion

    p = ((x ** 2) / (disp_w ** 2)) + ((y ** 2) / (disp_h ** 2))
    return p <= 1